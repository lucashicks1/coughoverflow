package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/aws/aws-sdk-go-v2/service/sqs/types"
)

type AnalysisMsg struct {
	RequestId    string `json:"request_id"`
	Urgent       bool   `json:"urgent"`
	EncodedImage string `json:"encoded_image"`
}

type AnalysisProcessor struct {
	client   *sqs.Client
	queueUrl string
	pool     *pgxpool.Pool
	jobs     chan types.Message
}

var engineOutputMap = map[string]string{
	"covid-19": "covid",
	"h5n1":     "h5n1",
	"healthy":  "healthy",
	"failed":   "failed",
}

func analyseImage(data AnalysisMsg) (string, error) {
	log.Printf("Starting image processing for RequestId=%s", data.RequestId)

	// Decode base64
	decodedImage, err := base64.StdEncoding.DecodeString(data.EncodedImage)
	if err != nil {
		// Message should contain valid base64
		log.Printf("Error decoding base64 image for RequestId=%s: %v", data.RequestId, err)
		return "failed", err
	}

	// Define file paths
	inputFilePath := fmt.Sprintf("%s-input.jpg", data.RequestId)
	outputFilePath := fmt.Sprintf("./%s-output.txt", data.RequestId)

	// Write the input file
	err = os.WriteFile(inputFilePath, decodedImage, 0644)
	if err != nil {
		log.Printf("Error writing input file (%s): %v", inputFilePath, err)
		return "", err
	}

	// Build and execute binary
	cmd := exec.Command("./overflowengine", "--input", inputFilePath, "--output", outputFilePath)
	_, err = cmd.CombinedOutput()

	if err != nil {
		log.Printf("Overflow engine returned error for RequestId=%s: %v", data.RequestId, err)
		return "failed", nil
	}

	// Read the output file
	resultBytes, err := os.ReadFile(outputFilePath)
	if err != nil {
		log.Printf("Error reading output file (%s): %v", outputFilePath, err)
		return "", err
	}
	result := strings.TrimSpace(string(resultBytes))

	// Clean up files
	go func() {
		_ = os.Remove(inputFilePath)
		_ = os.Remove(outputFilePath)

	}()

	// Map engine output to final status.
	finalStatus, ok := engineOutputMap[result]
	if !ok {
		finalStatus = "failed"
	}

	return finalStatus, nil
}

func (ap *AnalysisProcessor) processMessage(msg types.Message) {
	ctx := context.Background()

	// Unmarshal message
	var data AnalysisMsg
	if err := json.Unmarshal([]byte(*msg.Body), &data); err != nil {
		log.Printf("Error unmarshalling message (MessageId=%s): %v", *msg.MessageId, err)
		return
	}

	log.Printf("Processing message with id: %s (MessageId=%s)", data.RequestId, *msg.MessageId)

	// Process the image by calling the external engine.
	finalStatus, err := analyseImage(data)
	if err != nil {
		// If processing fails, redo processing
		log.Printf("Processing failed for RequestId=%s, returning early forcing reprocess", data.RequestId)
		return
	}
	log.Printf("Final status for RequestId=%s is set to: %s", data.RequestId, finalStatus)

	// Setup database connection
	dbConn, err := ap.pool.Acquire(ctx)
	if err != nil {
		log.Printf("Failed to acquire connection: %v", err)
		return
	}
	defer dbConn.Release()

	// Update analysis job with status
	_, err = dbConn.Exec(ctx,
		"UPDATE analysis_job SET result = $1, updated_at = NOW() WHERE id = $2",
		finalStatus,
		data.RequestId)

	if err != nil {
		log.Printf("Error updating database to %v for RequestId=%s: %v", finalStatus, data.RequestId, err)
		return
	}

	// Delete message
	dmi := &sqs.DeleteMessageInput{
		QueueUrl:      &ap.queueUrl,
		ReceiptHandle: msg.ReceiptHandle,
	}

	_, err = ap.client.DeleteMessage(
		ctx,
		dmi,
	)

	if err != nil {
		log.Printf("Failed to delete message with RequestId=%s: %v", data.RequestId, err)
	}

}

func (ap *AnalysisProcessor) worker(ctx context.Context, id int) {
	for {
		select {
		case <-ctx.Done():
			log.Printf("Worker %d exiting...", id)
			return
		case msg := <-ap.jobs:
			ap.processMessage(msg)
		}
	}
}

func (ap *AnalysisProcessor) startWorkerPool(ctx context.Context, numWorkers int) {
	for i := 0; i < numWorkers; i++ {
		go ap.worker(ctx, i)
	}
}

func (ap *AnalysisProcessor) pollQueue(ctx context.Context) {

	for {
		select {
		case <-ctx.Done():
			log.Println("Stopping queue polling...")
			return
		default:
		}

		resp, err := ap.client.ReceiveMessage(context.TODO(), &sqs.ReceiveMessageInput{
			QueueUrl:            aws.String(ap.queueUrl),
			MaxNumberOfMessages: 10,
			WaitTimeSeconds:     5,
		})
		if err != nil {
			log.Printf("Error receiving messages from the queue: %v", err)
			continue
		}

		messages := resp.Messages

		if len(messages) < 1 {
			time.Sleep(2 * time.Second)
			continue
		}

		for _, msg := range resp.Messages {
			select {
			case ap.jobs <- msg:
			case <-ctx.Done():
				return
			}
		}
	}
}

func main() {
	ctx := context.TODO()

	// Setting up DB
	dbURL, exists := os.LookupEnv("DB_URL")
	if !exists {
		log.Fatal("The database url is not set under 'DB_URL' env variable")
	}

	dbConfig, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		log.Fatalf("Failed to create a config, error: %v", err)
	}

	pool, err := pgxpool.NewWithConfig(ctx, dbConfig)
	if err != nil {
		log.Fatalf("Failed to create connection pool: %v", err)
	}
	defer pool.Close()

	// Test connection
	if err := pool.Ping(ctx); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}
	log.Println("Successfully connected to database")

	queueURL, exists := os.LookupEnv("AWS_SQS_URL")
	if !exists {
		log.Fatal("The sqs url is not set under 'AWS_SQS_URL' env variable")
	}

	numWorkersStr, exists := os.LookupEnv("NUM_WORKERS")
	numWorkers := 30 // Default value
	if exists {
		numWorkers, err = strconv.Atoi(numWorkersStr)
		if err != nil {
			log.Printf("Invalid NUM_WORKERS value: %s, using default of 30", numWorkersStr)
			numWorkers = 30
		}
	}

	// Load the AWS config
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatal(err)
	}

	processor := &AnalysisProcessor{
		client:   sqs.NewFromConfig((cfg)),
		queueUrl: queueURL,
		pool:     pool,
		jobs:     make(chan types.Message, 2*numWorkers),
	}

	processor.startWorkerPool(ctx, numWorkers)
	processor.pollQueue(ctx)
}
