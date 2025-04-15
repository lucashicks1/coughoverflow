package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

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

func handleMessage(msg types.Message, resultChan chan<- string) {
	var data AnalysisMsg
	if err := json.Unmarshal([]byte(*msg.Body), &data); err != nil {
		log.Printf("Error unmarshalling message (MessageId=%s): %v", *msg.MessageId, err)
		resultChan <- ""
		return
	}

	log.Printf("Processing message with id: %s (MessageId=%s)", data.RequestId, *msg.MessageId)

	resultChan <- *msg.ReceiptHandle
}

func main() {
	queueURL, exists := os.LookupEnv("AWS_SQS_NAME")
	if !exists {
		queueURL = "main"
	}
	urgentQueueURL, exists := os.LookupEnv("AWS_SQS_NAME_URGENT")
	if !exists {
		urgentQueueURL = "main_urgent"
	}
	var maxMessageNum int32 = 10

	// Load the AWS config
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatal(err)
	}

	client := sqs.NewFromConfig(cfg)
	ctx := context.TODO()

	for {
		var messages []types.Message
		currentQueueURL := urgentQueueURL

		resp, err := client.ReceiveMessage(context.TODO(), &sqs.ReceiveMessageInput{
			QueueUrl:            aws.String(urgentQueueURL),
			MaxNumberOfMessages: maxMessageNum,
		})
		if err != nil {
			log.Printf("Error receiving messages from urgent queue: %v", err)
			continue
		}

		messages = resp.Messages

		if len(messages) == 0 {
			currentQueueURL = queueURL
			resp, err := client.ReceiveMessage(context.TODO(), &sqs.ReceiveMessageInput{
				QueueUrl:            aws.String(queueURL),
				MaxNumberOfMessages: maxMessageNum,
				WaitTimeSeconds:     5,
			})
			if err != nil {
				log.Printf("Error receiving messages from normal queue: %v", err)
				continue
			}
			messages = resp.Messages
		}

		// If still no messages, wait a bit
		if len(messages) == 0 {
			time.Sleep(2 * time.Second)
			continue
		}

		resultChan := make(chan string, len(messages))

		for _, msg := range messages {
			go handleMessage(msg, resultChan)
		}

		var receiptHandles []string
		for i := 0; i < len(messages); i++ {
			rh := <-resultChan
			if rh != "" {
				receiptHandles = append(receiptHandles, rh)
			}
		}

		// Delete messages that are done
		if len(receiptHandles) > 0 {
			entries := make([]types.DeleteMessageBatchRequestEntry, len(messages))
			for msgIndex := range messages {
				entries[msgIndex].Id = aws.String(fmt.Sprintf("%v", msgIndex))
				entries[msgIndex].ReceiptHandle = messages[msgIndex].ReceiptHandle
			}

			_, err := client.DeleteMessageBatch(ctx, &sqs.DeleteMessageBatchInput{
				Entries:  entries,
				QueueUrl: aws.String(currentQueueURL),
			})
			if err != nil {
				log.Printf("Couldn't delete messages from queue %v. Here's why: %v\n", currentQueueURL, err)
			}
		}

	}
}
