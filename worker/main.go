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

func mustEnv(key string) string {
	val, ok := os.LookupEnv(key)
	if !ok {
		log.Fatalf("Missing env var: %s", key)
	}
	return val
}

func analyseImage(ctx context.Context, data AnalysisMsg) (string, error) {
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

	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	// Build and execute binary
	cmd := exec.CommandContext(ctx, "./overflowengine", "--input", inputFilePath, "--output", outputFilePath)
	output, err := cmd.CombinedOutput()

	if ctx.Err() == context.DeadlineExceeded {
		log.Printf("Engine timed out for RequestId=%s", data.RequestId)
		return "failed", ctx.Err()
	}

	if err != nil {
		log.Printf("Overflow engine error output: %s", string(output))
		log.Printf("Error: %v", err)
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
	defer os.Remove(inputFilePath)
	defer os.Remove(outputFilePath)

	// Map engine output to final status.
	finalStatus, ok := engineOutputMap[result]
	if !ok {
		finalStatus = "failed"
	}

	return finalStatus, nil
}

func (ap *AnalysisProcessor) processMessage(ctx context.Context, msg types.Message) {
	// Unmarshal message
	var data AnalysisMsg
	if err := json.Unmarshal([]byte(*msg.Body), &data); err != nil {
		log.Printf("Error unmarshalling message (MessageId=%s): %v", *msg.MessageId, err)
		return
	}

	log.Printf("Processing message with id: %s (MessageId=%s)", data.RequestId, *msg.MessageId)

	// Process the image by calling the external engine.
	finalStatus, err := analyseImage(ctx, data)
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
			ap.processMessage(ctx, msg)
		}
	}
}

func (ap *AnalysisProcessor) startWorkerPool(ctx context.Context, numWorkers int) {
	for i := range numWorkers {
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

		resp, err := ap.client.ReceiveMessage(ctx, &sqs.ReceiveMessageInput{
			QueueUrl:            aws.String(ap.queueUrl),
			MaxNumberOfMessages: 10,
			WaitTimeSeconds:     10,
		})
		if err != nil {
			log.Printf("Error receiving messages from the queue: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		messages := resp.Messages

		if len(messages) == 0 {
			log.Print("No messages, sleeping now...")
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

func getDb(context context.Context, dbUrl string) (*pgxpool.Pool, error) {
	dbConfig, err := pgxpool.ParseConfig(dbUrl)
	if err != nil {
		return nil, err
	}

	pool, err := pgxpool.NewWithConfig(context, dbConfig)
	if err != nil {
		return nil, err
	}

	// Test connection
	if err := pool.Ping(context); err != nil {
		return nil, fmt.Errorf("Failed to ping database: %w", err)
	}
	log.Println("Successfully connected to database")

	return pool, nil
}

func main() {
	ctx := context.Background()

	// Setting up DB
	dbUrl := mustEnv("DB_URL")

	pool, err := getDb(ctx, dbUrl)
	if err != nil {
		log.Fatal(err)
	}

	queueURL := mustEnv("AWS_SQS_URL")

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
	cfg, err := config.LoadDefaultConfig(ctx)
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
