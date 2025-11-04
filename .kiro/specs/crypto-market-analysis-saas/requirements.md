# Requirements Document

## Introduction

This document specifies the requirements for a private SaaS service that provides cryptocurrency market analysis and prediction capabilities. The system collects historical cryptocurrency price data, performs deep learning-based predictions, offers a generative AI-powered chat interface for market analysis, and provides real-time alerts for significant market shifts. The solution is built using Python, Flask, SQLAlchemy, and integrates with Binance API for data collection and OpenAI API for AI capabilities.

## Glossary

- **Crypto_Collector**: The component responsible for gathering and storing cryptocurrency price data from external sources
- **Data_Store**: The PostgreSQL database that persists cryptocurrency historical data
- **Prediction_Engine**: The deep learning component that analyzes historical data to forecast cryptocurrency performance
- **GenAI_Interface**: The generative AI-powered chat interface for market analysis queries
- **Alert_System**: The component that monitors market conditions and sends SMS notifications
- **Web_UI**: The user interface for interacting with the system, combining Streamlit for data visualization and HTML5/CSS/Bootstrap5 for the chat interface
- **API_Service**: The Flask-based REST API that exposes system functionality
- **PII_Filter**: The security component that detects and blocks personally identifiable information
- **Market_Shift**: A significant percentage change in cryptocurrency market capitalization or price within a defined timeframe

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to configure the data collection parameters through environment variables, so that I can control the collector behavior without modifying code

#### Acceptance Criteria

1. THE Crypto_Collector SHALL read the start date for historical data collection from the .env configuration file
2. THE Crypto_Collector SHALL read the number of top cryptocurrencies to track from the .env configuration file
3. THE Crypto_Collector SHALL read the schedule configuration for automated collection from the .env configuration file
4. THE Crypto_Collector SHALL read the Binance API credentials from the .env configuration file
5. THE Crypto_Collector SHALL read the OpenAI API key and model name from the .env configuration file

### Requirement 2

**User Story:** As a system administrator, I want to launch the data collector manually or on a schedule, so that I can control when cryptocurrency data is gathered

#### Acceptance Criteria

1. THE Crypto_Collector SHALL provide a manual execution mode that collects data when explicitly invoked
2. WHEN the schedule configuration is enabled, THE Crypto_Collector SHALL execute automatically at the configured intervals
3. WHEN launched, THE Crypto_Collector SHALL query the Data_Store to identify the most recent data timestamp
4. WHEN launched, THE Crypto_Collector SHALL query the Data_Store to identify gaps in historical data

### Requirement 3

**User Story:** As a system administrator, I want the collector to gather historical cryptocurrency data systematically, so that the database contains complete price history

#### Acceptance Criteria

1. WHEN collecting historical data, THE Crypto_Collector SHALL first retrieve data from yesterday backward to the start date defined in .env
2. WHEN backward collection is complete, THE Crypto_Collector SHALL retrieve data from the last recorded date forward to the most recent available data
3. THE Crypto_Collector SHALL store hourly cryptocurrency price data in USD for each tracked cryptocurrency
4. THE Crypto_Collector SHALL track the top N cryptocurrencies by market capitalization, where N is defined in .env
5. THE Crypto_Collector SHALL retrieve cryptocurrency data from the Binance free API

### Requirement 4

**User Story:** As a system administrator, I want cryptocurrency data persisted in a PostgreSQL database, so that historical information is reliably stored and queryable

#### Acceptance Criteria

1. THE Data_Store SHALL use PostgreSQL as the database management system
2. THE Data_Store SHALL store cryptocurrency price records with timestamp, cryptocurrency identifier, and USD price value
3. THE Data_Store SHALL support queries for retrieving historical data by cryptocurrency and time range
4. THE API_Service SHALL use SQLAlchemy as the ORM for database interactions

### Requirement 5

**User Story:** As an API consumer, I want to retrieve predictions for the best performing cryptocurrencies, so that I can make informed investment decisions

#### Acceptance Criteria

1. THE API_Service SHALL expose an endpoint that returns the top 20 cryptocurrencies predicted to perform best in the next 24 hours
2. THE Prediction_Engine SHALL use LSTM or GRU neural networks to generate performance predictions
3. THE Prediction_Engine SHALL base predictions on historical price data stored in the Data_Store
4. THE API_Service SHALL return predictions with cryptocurrency identifiers and predicted performance metrics

### Requirement 6

**User Story:** As an API consumer, I want to retrieve the current market tendency, so that I can understand overall market conditions

#### Acceptance Criteria

1. THE API_Service SHALL expose an endpoint that returns the current market tendency
2. THE Prediction_Engine SHALL classify market tendency into predefined categories (bullish, bearish, volatile, stable, consolidating)
3. THE Prediction_Engine SHALL calculate market tendency based on recent price movements and market capitalization changes
4. THE API_Service SHALL return the market tendency classification with supporting metrics

### Requirement 7

**User Story:** As a user, I want to interact with a chat interface to ask questions about cryptocurrency markets, so that I can gain insights through natural conversation

#### Acceptance Criteria

1. THE Web_UI SHALL provide a chat interface similar to ChatGPT for cryptocurrency market questions
2. THE GenAI_Interface SHALL use the OpenAI API with the gpt-4o-mini model (or model specified in .env) to generate responses
3. THE GenAI_Interface SHALL limit questions to cryptocurrency market and technology topics
4. WHEN a user submits a question outside the allowed topics, THE GenAI_Interface SHALL reject the question with an appropriate message
5. THE Web_UI SHALL display the conversation history limited to the most recent 3 question-answer pairs

### Requirement 8

**User Story:** As a security officer, I want all interactions with OpenAI to be anonymous and free of personal data, so that user privacy and enterprise information are protected

#### Acceptance Criteria

1. WHEN a user submits a question, THE PII_Filter SHALL analyze the question for personally identifiable information
2. IF the PII_Filter detects personal data in a question, THEN THE GenAI_Interface SHALL reject the question and display a security warning
3. THE GenAI_Interface SHALL not transmit any enterprise-specific information to the OpenAI API
4. THE PII_Filter SHALL detect common PII patterns including names, email addresses, phone numbers, addresses, and financial account numbers
5. THE GenAI_Interface SHALL sanitize all data before sending requests to external AI services

### Requirement 9

**User Story:** As a user, I want to receive SMS alerts for significant market shifts, so that I can respond quickly to important market events

#### Acceptance Criteria

1. THE Alert_System SHALL monitor cryptocurrency market data every hour
2. WHEN the Alert_System detects a massive market shift (increase or decrease beyond a threshold), THE Alert_System SHALL send an SMS notification
3. THE Alert_System SHALL send SMS messages to the phone number configured in the .env file
4. THE Alert_System SHALL define market shift thresholds as configurable parameters
5. THE Alert_System SHALL include relevant market information in SMS notifications (affected cryptocurrencies, percentage change, timestamp)

### Requirement 10

**User Story:** As a developer, I want the system built with Python and open-source tools, so that the solution is maintainable and cost-effective

#### Acceptance Criteria

1. THE API_Service SHALL be implemented using the Flask web framework
2. THE API_Service SHALL use SQLAlchemy for database operations
3. THE Web_UI SHALL be implemented using Streamlit for data visualization and dashboards
4. THE Web_UI SHALL use HTML5, CSS, and Bootstrap5 for the chat interface
5. THE Prediction_Engine SHALL use open-source deep learning libraries (TensorFlow or PyTorch)
6. THE system SHALL use only open-source and free tools except for the OpenAI API

### Requirement 11

**User Story:** As a system administrator, I want to deploy the service on AWS with clear separation between local and remote infrastructure, so that I can manage deployments efficiently

#### Acceptance Criteria

1. THE system SHALL provide Terraform configuration in a terraform/ folder for AWS infrastructure provisioning
2. THE system SHALL deploy to an Amazon Linux 2023 t3.micro EC2 instance in a public subnet
3. THE system SHALL configure a Security Group that allows SSH (port 22) and HTTPS (port 443) access only from the developer workstation IP address
4. THE system SHALL enable AWS Systems Manager (SSM) and EC2 Instance Connect for secure access
5. THE system SHALL provision an Elastic IP (EIP) for the EC2 instance
6. THE system SHALL install PostgreSQL directly on the EC2 instance for the initial deployment
7. THE system SHALL support future migration to RDS PostgreSQL as an evolution path
8. THE system SHALL maintain clear separation between local deployment scripts and remote application scripts
9. THE system SHALL be accessible via crypto-ai.local:10443 for local development environment
10. THE system SHALL be accessible via crypto-ai.crypto-vision.com for AWS production environment
11. THE system SHALL use self-signed SSL certificates for both local and AWS environments

### Requirement 12

**User Story:** As a developer, I want to run the system in both local and AWS environments with environment-specific configurations, so that I can develop and test before deploying to production

#### Acceptance Criteria

1. THE system SHALL support a local development environment using an external local PostgreSQL database
2. THE system SHALL support an AWS environment using PostgreSQL installed on EC2
3. THE system SHALL use .env files to configure database connection parameters for each environment
4. THE system SHALL provide a local-env.example file for local development configuration
5. THE system SHALL provide an aws-env.example file for AWS deployment configuration
6. THE system SHALL read database connection parameters from environment variables to support both environments

### Requirement 13

**User Story:** As a user, I want comprehensive documentation, so that I can understand how to develop, deploy, use, and secure the system

#### Acceptance Criteria

1. THE system SHALL include a DEVELOPMENT-GUIDE.md document that covers setup, OpenAI registration, and development workflows
2. THE system SHALL include a DEPLOYMENT-GUIDE.md document that covers AWS deployment procedures using Terraform
3. THE system SHALL include a USER-GUIDE.md document that covers system usage and cost estimates
4. THE system SHALL include a SECURITY-CONFORMANCE-GUIDE.md document that covers security practices and compliance considerations
