package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
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

var engineOutputMap = map[string]string{
	"covid-19": "covid",
	"h5n1":     "h5n1",
	"healthy":  "healthy",
	"failed":   "failed",
}

func handleMessage(pool *pgxpool.Pool, msg types.Message, resultChan chan<- *string) {
	ctx := context.Background()

	// Setup database connection
	dbConn, err := pool.Acquire(ctx)
	if err != nil {
		log.Printf("Failed to acquire connection: %v", err)
		resultChan <- nil
		return
	}
	defer dbConn.Release()

	// Unmarshal message
	var data AnalysisMsg
	if err := json.Unmarshal([]byte(*msg.Body), &data); err != nil {
		log.Printf("Error unmarshalling message (MessageId=%s): %v", *msg.MessageId, err)
		resultChan <- nil
		return
	}

	// Process the image by calling the external engine.
	finalStatus, err := processImage(data)
	if err != nil {
		// If processing fails, update db with "failed"
		finalStatus = "failed"
		log.Printf("Processing failed for RequestId=%s", data.RequestId)
	}

	// Update analysis job with status
	_, errUpdate := dbConn.Exec(ctx,
		"UPDATE analysis_job SET result = $1, updated_at = NOW() WHERE id = $2",
		finalStatus,
		data.RequestId)
	if errUpdate != nil {
		log.Printf("Error updating database to %v for RequestId=%s: %v", finalStatus, data.RequestId, errUpdate)
		resultChan <- nil
		return
	}

	log.Printf("Processing message with id: %s (MessageId=%s)", data.RequestId, *msg.MessageId)

	resultChan <- aws.String(*msg.ReceiptHandle)
}

func processImage(data AnalysisMsg) (string, error) {
	log.Printf("Starting image processing for RequestId=%s", data.RequestId)

	// Decode base64
	decodedImage, err := base64.StdEncoding.DecodeString(data.EncodedImage)
	if err != nil {
		log.Printf("Error decoding base64 image for RequestId=%s: %v", data.RequestId, err)
		return "", err
	}
	log.Printf("Image decoded successfully for RequestId=%s", data.RequestId)

	// Define file paths
	inputFilePath := fmt.Sprintf("%s-input.jpg", data.RequestId)
	outputFilePath := fmt.Sprintf("./%s-output.txt", data.RequestId)

	// Write the input file
	log.Printf("Writing input file: %s", inputFilePath)
	err = os.WriteFile(inputFilePath, decodedImage, 0644)
	if err != nil {
		log.Printf("Error writing input file (%s): %v", inputFilePath, err)
		return "", err
	}
	log.Printf("Input file written successfully: %s", inputFilePath)

	// Build and execute binary
	log.Printf("Starting overflow engine process with input=%s and output=%s", inputFilePath, outputFilePath)
	cmd := exec.Command("./overflowengine", "--input", inputFilePath, "--output", outputFilePath)
	output, err := cmd.CombinedOutput()
	log.Printf("Overflow engine process completed for RequestId=%s", data.RequestId)
	log.Printf("Engine output: %s", string(output))
	if err != nil {
		log.Printf("Overflow engine returned error for RequestId=%s: %v", data.RequestId, err)
		return "", err
	}

	// Read the output file
	log.Printf("Reading output file: %s", outputFilePath)
	resultBytes, err := os.ReadFile(outputFilePath)
	if err != nil {
		log.Printf("Error reading output file (%s): %v", outputFilePath, err)
		return "", err
	}
	result := strings.TrimSpace(string(resultBytes))
	log.Printf("Engine returned result for RequestId=%s: %s", data.RequestId, result)

	// Clean up files
	err = os.Remove(inputFilePath)
	if err != nil {
		log.Printf("Warning: unable to remove input file %s: %v", inputFilePath, err)
	}
	err = os.Remove(outputFilePath)
	if err != nil {
		log.Printf("Warning: unable to remove output file %s: %v", outputFilePath, err)
	}

	// Map engine output to final status.
	finalStatus, ok := engineOutputMap[result]
	if !ok {
		finalStatus = "failed"
	}

	log.Printf("Final status for RequestId=%s is set to: %s", data.RequestId, finalStatus)
	return finalStatus, nil
}

func main() {
	ctx := context.TODO()

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

	var maxMessageNum int32 = 10

	// Load the AWS config
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatal(err)
	}

	client := sqs.NewFromConfig(cfg)

	for {
		fmt.Print("Running loop checking for messages.")
		var messages []types.Message

		resp, err := client.ReceiveMessage(context.TODO(), &sqs.ReceiveMessageInput{
			QueueUrl:            aws.String(queueURL),
			MaxNumberOfMessages: maxMessageNum,
			WaitTimeSeconds:     5,
		})
		if err != nil {
			log.Printf("Error receiving messages from the queue: %v", err)
			continue
		}

		messages = resp.Messages

		if len(messages) == 0 {
			time.Sleep(2 * time.Second)
			continue
		}

		resultChan := make(chan *string, len(messages))

		startTime := time.Now()
		for _, msg := range messages {
			go handleMessage(pool, msg, resultChan)
		}
		endTime := time.Now()

		entries := []types.DeleteMessageBatchRequestEntry{}
		var entry types.DeleteMessageBatchRequestEntry
		for i := 0; i < len(messages); i++ {
			rh := <-resultChan
			if rh != nil {
				entry = types.DeleteMessageBatchRequestEntry{Id: aws.String(fmt.Sprintf("%v", i)), ReceiptHandle: rh}
				entries = append(entries, entry)
			}
		}
		fmt.Printf("Handled %v messages in %v\n", len(messages), endTime.Sub(startTime))

		// Delete messages that are done
		if len(entries) > 0 {
			fmt.Printf("Deleting %v messages", entries)
			_, err := client.DeleteMessageBatch(ctx, &sqs.DeleteMessageBatchInput{
				Entries:  entries,
				QueueUrl: aws.String(queueURL),
			})
			if err != nil {
				log.Printf("Couldn't delete messages from queue %v. Here's why: %v\n", queueURL, err)
			}
		}

	}
}
