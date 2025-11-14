# Implementation Plan

- [x] 1. Set up project structure and core configuration




  - Create Python project structure with src/ directory for main application code
  - Set up virtual environment and requirements.txt with core dependencies (Flask, SQLAlchemy, psycopg2, python-dotenv, requests)
  - Create .env.example file with all required configuration variables
  - Implement configuration loader module to read and validate environment variables
  - Set up logging configuration with file and console handlers
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
- [x] 2. Implement database layer with SQLAlchemy models




- [ ] 2. Implement database layer with SQLAlchemy models

  - [x] 2.1 Create database connection and session management


    - Implement database connection factory using SQLAlchemy
    - Create session management with connection pooling
    - Add database initialization script for creating tables
    - _Requirements: 4.1, 4.4_
  
  - [x] 2.2 Define SQLAlchemy models for all entities


    - Create Cryptocurrency model with symbol, name, market_cap_rank fields
    - Create PriceHistory model with crypto_id, timestamp, price_usd, volume_24h, market_cap fields
    - Create Prediction model with crypto_id, prediction_date, predicted_price, confidence_score fields
    - Create ChatHistory model with session_id, question, answer, context_used, token counts, cost tracking
    - Create QueryAuditLog model for security and compliance tracking
    - Create MarketTendency model for tendency classification storage
    - Add appropriate indexes for query optimization
    - _Requirements: 4.2, 4.3_
  
  - [x] 2.3 Implement repository pattern for data access


    - Create CryptoRepository with methods for CRUD operations on cryptocurrencies
    - Create PriceHistoryRepository with methods for querying historical data by crypto and time range
    - Create PredictionRepository for storing and retrieving predictions
    - Create ChatHistoryRepository with session-based queries (last 3 Q&A pairs)
    - Create AuditLogRepository for security logging
    - _Requirements: 4.3_

- [x] 3. Build Binance API client and data collector




  - [x] 3.1 Implement Binance API client wrapper


    - Create BinanceClient class with methods for fetching hourly price data
    - Implement get_top_by_market_cap() to retrieve top N cryptocurrencies
    - Add retry logic with exponential backoff for API failures
    - Implement rate limiting to respect Binance API limits
    - _Requirements: 3.5, 1.4_
  
  - [x] 3.2 Implement data gap detection logic


    - Create DataGapDetector class to identify missing time ranges in database
    - Implement method to find gaps between start_date and yesterday
    - Implement method to find gaps between last recorded date and current date
    - _Requirements: 2.4_
  
  - [x] 3.3 Build crypto data collector orchestrator


    - Create CryptoCollector class as main orchestrator
    - Implement collect_backward() method to gather data from yesterday to start_date
    - Implement collect_forward() method to gather data from last recorded date to present
    - Add logic to track top N cryptocurrencies by market cap from .env
    - Implement data persistence using PriceHistoryRepository
    - Add progress tracking and logging
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_
  
  - [x] 3.4 Implement collector scheduler


    - Create CollectorScheduler using APScheduler or similar library
    - Read schedule configuration from .env (cron expression)
    - Implement manual trigger endpoint for admin control
    - Add status tracking (running, idle, error states)
    - _Requirements: 2.1, 2.2_
- [x] 4. Develop LSTM/GRU prediction engine



- [ ] 4. Develop LSTM/GRU prediction engine

  - [x] 4.1 Implement data preprocessing pipeline


    - Create DataPreprocessor class for feature engineering
    - Implement price normalization (MinMaxScaler)
    - Add technical indicators calculation (RSI, MACD, Bollinger Bands)
    - Create sequence generation for time series (e.g., 168-hour windows)
    - Implement train/validation/test split logic
    - _Requirements: 5.3_
  
  - [x] 4.2 Build LSTM/GRU model architecture


    - Create LSTMModel class using TensorFlow/Keras or PyTorch
    - Implement model architecture with 2-3 LSTM/GRU layers (64-128 units)
    - Add dropout layers (0.2-0.3) for regularization
    - Implement output layer for 24-hour price prediction
    - Create model save/load functionality
    - _Requirements: 5.2, 10.4_
  
  - [x] 4.3 Implement model training pipeline


    - Create ModelTrainer class for training orchestration
    - Implement training loop with early stopping and checkpointing
    - Add validation metrics calculation (MAE, RMSE, MAPE)
    - Implement model versioning and artifact storage (S3 or local)
    - Create training scheduler for periodic retraining
    - _Requirements: 5.2_
  
  - [x] 4.4 Build prediction engine for top performers


    - Create PredictionEngine class as main interface
    - Implement predict_top_performers() to generate predictions for all tracked cryptos
    - Add ranking logic to identify top 20 by predicted performance
    - Implement confidence score calculation
    - Add prediction caching to database
    - _Requirements: 5.1, 5.2, 5.4_
  
  - [x] 4.5 Implement market tendency classification


    - Create MarketTendencyClassifier class
    - Implement logic to classify market as bullish, bearish, volatile, stable, or consolidating
    - Calculate metrics: average change percent, volatility index, market cap change
    - Add confidence score calculation for tendency classification
    - Store tendency results in database
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
-

- [x] 5. Create GenAI engine with OpenAI integration



  - [x] 5.1 Implement PII detection and filtering


    - Create PIIFilter class with regex patterns for email, phone, addresses
    - Integrate spaCy for Named Entity Recognition (NER) to detect names
    - Add patterns for financial data (credit cards, bank accounts)
    - Implement sanitization method to remove detected PII
    - Create comprehensive test cases for PII detection accuracy
    - _Requirements: 8.1, 8.2, 8.4, 8.5_
  
  - [x] 5.2 Build topic validation system


    - Create TopicValidator class to ensure crypto-related questions
    - Implement keyword-based validation for allowed topics (crypto, blockchain, DeFi, etc.)
    - Add rejection logic for non-crypto topics (weather, sports, politics)
    - Create user-friendly rejection messages
    - _Requirements: 7.3, 7.4_
  
  - [x] 5.3 Implement context builder for enriched prompts


    - Create ContextBuilder class to aggregate internal data
    - Implement get_lstm_predictions() to fetch relevant predictions
    - Implement get_market_tendency() to retrieve current market state
    - Implement get_recent_price_data() for historical context
    - Create method to format context as text for OpenAI prompt
    - _Requirements: 5.1, 5.4, 6.1, 6.4_
  
  - [x] 5.4 Build OpenAI API integration


    - Create GenAIEngine class for OpenAI communication
    - Implement process_query() method with full workflow (validate, filter, build context, call API)
    - Configure OpenAI client with API key and model from .env
    - Implement system prompt for crypto-focused assistant
    - Add token counting and cost tracking
    - Implement error handling for API failures with fallback responses
    - _Requirements: 7.2, 7.5, 8.3, 8.5, 1.5_
  
  - [x] 5.5 Implement chat history management


    - Create ChatHistoryManager class for conversation tracking
    - Implement method to retrieve last 3 Q&A pairs for session
    - Add method to store new chat messages with full tracing data
    - Implement audit logging for all queries (security and compliance)
    - _Requirements: 7.5_

- [x] 6. Build Flask REST API service



  - [x] 6.1 Set up Flask application and middleware


    - Create Flask app with blueprints for different API sections
    - Implement CORS configuration for web UI access
    - Add request logging middleware
    - Implement API key authentication middleware
    - Add rate limiting middleware (100 requests/minute)
    - _Requirements: 10.1_
  
  - [x] 6.2 Implement prediction endpoints


    - Create /api/predictions/top20 GET endpoint
    - Integrate with PredictionEngine to fetch top performers
    - Format response with predictions, confidence scores, and metadata
    - Add caching headers for performance
    - _Requirements: 5.1, 5.4_
  
  - [x] 6.3 Implement market tendency endpoint


    - Create /api/market/tendency GET endpoint
    - Integrate with PredictionEngine for tendency classification
    - Format response with tendency, confidence, and metrics
    - _Requirements: 6.1, 6.4_
  
  - [x] 6.4 Implement chat query endpoint


    - Create /api/chat/query POST endpoint
    - Integrate with GenAIEngine for query processing
    - Handle session management for conversation continuity
    - Return answer with chat history (last 3 Q&A pairs)
    - Add error responses for PII detection and topic validation failures
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2_
  
  - [x] 6.5 Implement admin endpoints for data collection


    - Create /api/admin/collect/trigger POST endpoint for manual collection
    - Create /api/admin/collect/status GET endpoint for progress tracking
    - Add authentication check for admin-only access
    - _Requirements: 2.1_
  
  - [x] 6.6 Implement error handling and response formatting


    - Create standardized error response format with error codes
    - Add exception handlers for common errors (404, 500, etc.)
    - Implement request validation for all endpoints
    - Add API documentation using Flask-RESTX or similar
    - _Requirements: All API-related requirements_

- [x] 7. Develop alert system for market shifts




  - [x] 7.1 Implement market shift detection


    - Create MarketMonitor class to analyze hourly price changes
    - Implement detect_massive_shift() with configurable threshold from .env
    - Calculate percentage changes for all tracked cryptocurrencies
    - Identify both increases and decreases beyond threshold
    - Add cooldown logic to prevent alert spam (max 1 per crypto per 4 hours)
    - _Requirements: 9.1, 9.2, 9.4_
  
  - [x] 7.2 Build SMS gateway integration


    - Create SMSGateway interface for multiple providers
    - Implement Twilio integration as primary option
    - Implement AWS SNS integration as alternative
    - Read SMS configuration from .env (provider, phone number, credentials)
    - Add retry logic for failed SMS sends
    - _Requirements: 9.3_
  
  - [x] 7.3 Create alert system orchestrator


    - Create AlertSystem class as main coordinator
    - Implement check_market_shifts() to run hourly analysis
    - Format alert messages with crypto symbol, change percent, prices, timestamp
    - Integrate with SMSGateway to send notifications
    - Add alert logging to database for audit trail
    - _Requirements: 9.1, 9.2, 9.5_
  
  - [x] 7.4 Implement alert scheduler




    - Create AlertScheduler using APScheduler
    - Configure hourly execution from .env
    - Add error handling and retry logic
    - Implement status tracking and health checks
    - _Requirements: 9.1_

- [x] 8. Build Streamlit dashboard for data visualization



  - [x] 8.1 Create main dashboard layout


    - Set up Streamlit app structure with multiple pages
    - Create navigation sidebar for different views
    - Implement market overview page with key metrics
    - Add real-time data refresh functionality
    - _Requirements: 10.3_
  
  - [x] 8.2 Implement predictions visualization


    - Create predictions page displaying top 20 performers
    - Add interactive charts using Plotly or Chart.js (bar charts, line charts)
    - Display prediction confidence scores with visual indicators
    - Add filtering and sorting options
    - _Requirements: 5.1, 5.4, 10.3_
  
  - [x] 8.3 Build market tendency dashboard


    - Create market tendency page with historical trends
    - Display current tendency with confidence indicator
    - Add charts showing tendency changes over time
    - Include supporting metrics visualization
    - _Requirements: 6.1, 6.4, 10.3_
  
  - [x] 8.4 Implement data collection status view


    - Create admin page for collection monitoring
    - Display collection progress, status, and statistics
    - Add manual trigger button for data collection
    - Show data coverage and gap information
    - _Requirements: 2.1, 2.2, 10.3_

- [x] 9. Create Bootstrap5 chat interface



  - [x] 9.1 Build HTML/CSS chat UI structure


    - Create chat.html template with Bootstrap5 components
    - Implement responsive layout for mobile and desktop
    - Design message bubbles for user questions and AI responses
    - Add input field with send button
    - Create loading indicator for processing state
    - _Requirements: 7.1, 10.4_
  
  - [x] 9.2 Implement JavaScript for chat interactions


    - Write JavaScript to handle message sending via AJAX
    - Implement real-time message display in chat window
    - Add auto-scroll to latest message
    - Handle error states (PII detected, invalid topic)
    - Display chat history (last 3 Q&A pairs) on page load
    - _Requirements: 7.1, 7.5, 10.4_
  
  - [x] 9.3 Integrate chat UI with Flask backend


    - Create Flask route to serve chat.html template
    - Connect JavaScript to /api/chat/query endpoint
    - Implement session management for conversation continuity
    - Add CSRF protection for form submissions
    - _Requirements: 7.1, 7.2, 10.1, 10.4_
  
  - [x] 9.4 Add user feedback and validation messages


    - Display PII detection warnings with user-friendly messages
    - Show topic validation errors for non-crypto questions
    - Add success indicators for sent messages
    - Implement typing indicator while waiting for response
    - _Requirements: 7.4, 8.2_

- [ ] 10. Implement security and compliance features


  - [x] 10.1 Set up secrets management



    - Integrate AWS Secrets Manager for production credentials
    - Implement local .env file loading for development
    - Create secrets rotation mechanism for API keys
    - Add validation to ensure no secrets in logs
    - _Requirements: 8.3, 8.5_
  
  - [x] 10.2 Implement API authentication and authorization



    - Create API key generation and management system
    - Implement middleware to validate API keys on all endpoints
    - Add role-based access control (admin vs regular user)
    - Implement API key rotation policy
    - _Requirements: 8.3_
  
  - [x] 10.3 Add input validation and sanitization



    - Implement request validation for all API endpoints
    - Add SQL injection prevention (parameterized queries)
    - Implement XSS protection for web UI
    - Add CSRF token validation for forms
    - _Requirements: 8.3, 8.5_
  
  - [x] 10.4 Implement comprehensive audit logging







    - Ensure all queries logged to query_audit_log table
    - Log PII detection events with patterns found
    - Track OpenAI API usage and costs
    - Implement log retention policies
    - Add admin dashboard for audit log review
    - _Requirements: 8.2, 8.5_

- [x] 11. Create Terraform infrastructure configuration


  - [x] 11.1 Set up Terraform project structure




    - Create terraform/ directory with main.tf, variables.tf, outputs.tf
    - Define Terraform backend configuration for state management
    - Create terraform.tfvars.example with required variables
    - Document Terraform version requirements
    - _Requirements: 11.1_
  
  - [x] 11.2 Implement EC2 instance configuration


    - Define Amazon Linux 2023 t3.micro instance resource
    - Configure Elastic IP and associate with instance
    - Create IAM role for SSM and CloudWatch access
    - Write user-data.sh script for initial instance setup
    - Configure EBS volumes (root + PostgreSQL data)
    - _Requirements: 11.2, 11.5_
  
  - [x] 11.3 Create Security Group configuration

    - Define security group with SSH (port 22) ingress from developer IP
    - Add HTTPS (port 443) ingress from developer IP
    - Configure all outbound traffic allowed
    - Use variables for developer workstation IP address
    - _Requirements: 11.3_
  
  - [x] 11.4 Configure EC2 access methods

    - Enable EC2 Instance Connect in Terraform
    - Configure IAM role for Systems Manager (SSM) Session Manager
    - Set up SSH key pair for direct access
    - Document access methods in outputs
    - _Requirements: 11.4_
  
  - [x] 11.5 Create Terraform outputs

    - Output Elastic IP address
    - Output EC2 instance ID
    - Output Security Group ID
    - Output connection commands for SSH and SSM
    - _Requirements: 11.5_

- [ ] 12. Implement local deployment scripts



  - [x] 12.1 Create local environment setup script


    - Write local-scripts/setup-local-env.sh for initial setup
    - Install Python dependencies in virtual environment
    - Set up local PostgreSQL database
    - Generate self-signed SSL certificate for crypto-ai.local:10443
    - Copy local-env.example to local-env and prompt for configuration
    - _Requirements: 12.1, 11.9, 11.11_
  
  - [x] 12.2 Create SSL certificate generation script




    - Write local-scripts/generate-ssl-cert.sh for self-signed certificates
    - Generate certificates for crypto-ai.local (local environment)
    - Generate certificates for crypto-ai.crypto-vision.com (AWS environment)
    - Store certificates in certs/ directory with proper permissions
    - _Requirements: 11.11_
  
  - [x] 12.3 Build AWS deployment script


    - Write local-scripts/deploy-to-aws.sh for full deployment
    - Sync application code to EC2 instance using rsync or scp
    - Execute remote-scripts/install-dependencies.sh on EC2
    - Execute remote-scripts/setup-postgresql.sh on EC2
    - Execute remote-scripts/setup-application.sh on EC2
    - Start services using remote-scripts/start-services.sh
    - _Requirements: 11.8_
  
  - [x] 12.4 Create code synchronization script


    - Write local-scripts/sync-code.sh for incremental updates
    - Sync only changed files to reduce transfer time
    - Exclude .git, __pycache__, and other unnecessary files
    - Restart services after sync
    - _Requirements: 11.8_
  
  - [x] 12.5 Implement remote control script


    - Write local-scripts/control-remote.sh for service management
    - Add start command to start all services on EC2
    - Add stop command to stop all services on EC2
    - Add status command to check service health
    - Add logs command to tail application logs
    - _Requirements: 11.8_


- [ ] 13. Implement remote application scripts



  - [x] 13.1 Create dependency installation script






    - Write remote-scripts/install-dependencies.sh for system packages
    - Install Python 3.10+, pip, virtualenv
    - Install PostgreSQL client libraries
    - Install system dependencies for ML libraries (numpy, scipy)
    - Create application user and directories
    - _Requirements: 11.8_
  
  - [x] 13.2 Build PostgreSQL setup script



    - Write remote-scripts/setup-postgresql.sh for database installation
    - Install PostgreSQL 15 on Amazon Linux 2023
    - Configure PostgreSQL to use separate EBS volume for data
    - Create crypto_db database and crypto_user
    - Configure PostgreSQL for local connections
    - Run database migrations to create schema





    - _Requirements: 11.6, 12.3_
  
  - [x] 13.3 Create application setup script




    - Write remote-scripts/setup-application.sh for app configuration
    - Create Python virtual environment
    - Install Python dependencies from requirements.txt
    - Copy aws-env to .env and configure database connection


    - Set up systemd service files for Flask, Streamlit, and schedulers

    - Configure Nginx as reverse proxy for HTTPS
    - Install and configure self-signed SSL certificate
    - _Requirements: 11.8, 11.10, 11.11_





  
  - [ ] 13.4 Implement service control scripts
    - Write remote-scripts/start-services.sh to start all services
    - Write remote-scripts/stop-services.sh to stop all services
    - Write remote-scripts/restart-services.sh to restart services





    - Add health check logic to verify services are running
    - _Requirements: 11.8_


  



  - [x] 13.5 Create database backup script

    - Write remote-scripts/backup-database.sh for PostgreSQL backups
    - Use pg_dump to create database backups
    - Compress backups and store with timestamp
    - Implement backup rotation (keep last 7 days)

    - Add option to upload backups to S3 (future enhancement)
    - _Requirements: 11.6_

- [ ] 14. Create environment configuration files

  - [x] 14.1 Create local environment template

    - Write local-env.example with all required variables


    - Set database URL for local PostgreSQL
    - Configure crypto-ai.local:10443 as Web UI URL
    - Set appropriate defaults for local development
    - Add comments explaining each variable

    - _Requirements: 12.1, 12.4, 12.5_


  



  - [x] 14.2 Create AWS environment template



    - Write aws-env.example with all required variables
    - Set database URL for EC2-hosted PostgreSQL
    - Configure crypto-ai.crypto-vision.com as Web UI URL

    - Set production-appropriate defaults
    - Add security warnings for sensitive values
    - _Requirements: 12.2, 12.4, 12.5_
  
  - [ ] 14.3 Implement environment variable validation
    - Create config validation module to check required variables

    - Validate database connection on startup
    - Verify SSL certificate paths exist
    - Check API keys are not using example values in production
    - _Requirements: 12.6_




- [ ] 15. Implement database migration system

  - [ ] 15.1 Set up Alembic for schema migrations
    - Initialize Alembic in project
    - Configure Alembic to use SQLAlchemy models
    - Create alembic.ini with environment-specific settings

    - _Requirements: 11.6_
  
  - [ ] 15.2 Create initial database migration
    - Generate initial migration from SQLAlchemy models
    - Include all tables: cryptocurrencies, price_history, predictions, chat_history, query_audit_log, market_tendencies
    - Add indexes and constraints

    - Test migration on clean database
    - _Requirements: 11.6_
  
  - [ ] 15.3 Add migration helper scripts
    - Create script to run migrations (upgrade)
    - Create script to rollback migrations (downgrade)


    - Add script to check current migration version



    - Document migration workflow in DEVELOPMENT-GUIDE.md
    - _Requirements: 11.6_

- [x] 16. Configure web server and HTTPS


  - [ ] 16.1 Set up Nginx as reverse proxy
    - Install Nginx on EC2 instance
    - Configure Nginx to proxy requests to Flask (port 5000)
    - Configure Nginx to proxy requests to Streamlit (port 8501)
    - Set up HTTPS on port 443 with self-signed certificate
    - _Requirements: 11.10, 11.11_
  
  - [ ] 16.2 Configure SSL/TLS for both environments
    - Generate self-signed certificate for crypto-ai.local
    - Generate self-signed certificate for crypto-ai.crypto-vision.com
    - Configure Nginx to use SSL certificates
    - Set up HTTP to HTTPS redirect
    - _Requirements: 11.11_
  
  - [ ] 16.3 Implement systemd service files
    - Create systemd service for Flask API
    - Create systemd service for Streamlit dashboard
    - Create systemd service for data collector scheduler
    - Create systemd service for alert system scheduler
    - Configure services to start on boot
    - _Requirements: 11.8_

- [ ] 17. Create AWS deployment configuration (future RDS evolution)

  - [ ] 17.1 Document RDS migration path
    - Create documentation for migrating from EC2 PostgreSQL to RDS
    - Document data migration procedure using pg_dump/pg_restore
    - Update Terraform configuration for RDS (commented out for future use)
    - Document cost implications of RDS migration
    - _Requirements: 11.7_
  
  - [ ] 17.2 Prepare Terraform for future scaling
    - Add commented Terraform resources for ALB
    - Add commented Terraform resources for Auto Scaling Group
    - Add commented Terraform resources for RDS PostgreSQL
    - Add commented Terraform resources for NAT Gateway
    - Document activation steps for each component
    - _Requirements: 11.7_

- [ ] 18. Write comprehensive documentation



  - [x] 18.1 Create DEVELOPMENT-GUIDE.md


    - Document local development setup steps using setup-local-env.sh
    - Include OpenAI API registration process with step-by-step instructions
    - Explain project structure and architecture
    - Document local-scripts/ and remote-scripts/ separation
    - Add instructions for running tests
    - Document database migration workflow
    - Explain how to add new features
    - _Requirements: 13.1_
  
  - [x] 18.2 Create DEPLOYMENT-GUIDE.md



    - Document AWS account setup requirements
    - Provide step-by-step Terraform deployment instructions
    - Document EC2 instance provisioning process
    - Explain PostgreSQL installation on EC2
    - Document deployment script usage (deploy-to-aws.sh)
    - Include environment variable configuration for aws-env
    - Add SSL certificate setup instructions
    - Document service management using control-remote.sh
    - Add troubleshooting section for common deployment issues
    - Include future RDS migration path
    - _Requirements: 13.2_
  
  - [x] 18.3 Create USER-GUIDE.md


    - Document how to access the system (local and AWS URLs)






    - Explain Streamlit dashboard usage and features
    - Document chat interface usage and limitations
    - Provide API endpoint documentation with curl examples
    - Include cost estimates for AWS services (t3.micro, EBS, data transfer)
    - Include cost estimates for OpenAI usage
    - Add FAQ section for common questions
    - Document alert system configuration
    - _Requirements: 13.3_
  
  - [x] 18.4 Create SECURITY-CONFORMANCE-GUIDE.md


    - Document PII protection mechanisms
    - Explain security best practices implemented
    - Document Security Group configuration and IP restrictions
    - Explain SSL/TLS setup with self-signed certificates
    - Include compliance considerations (GDPR, data retention)
    - Document audit logging and monitoring
    - Explain query tracing and cost tracking
    - Add incident response procedures
    - Document secrets management best practices
    - _Requirements: 13.4_
  
  - [ ] 18.5 Create REST-API-GUIDE.md
    - Document all API endpoints with full specifications
    - Include authentication and authorization requirements
    - Provide request/response examples for each endpoint
    - Document error codes and error handling
    - Include rate limiting information
    - Add curl examples for testing endpoints
    - Document API versioning strategy
    - Include pagination details where applicable
    - _Requirements: 13.5_

- [ ] 19. Wire everything together and create entry points






  - Create main.py as application entry point that initializes all components
  - Implement startup sequence: database connection, model loading, scheduler initialization
  - Create separate entry points for Flask API, Streamlit dashboard, and background workers
  - Add health check endpoints for monitoring
  - Implement graceful shutdown handling
  - Ensure environment-specific configuration loading (local-env vs aws-env)
  - Add startup validation to check all required services are available
  - _Requirements: All requirements_
