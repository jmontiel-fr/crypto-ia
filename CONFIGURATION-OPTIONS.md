# Configuration Options - Quick Reference

## Overview

This project provides multiple configuration templates for different use cases.

## Local Development

### Option 1: SQLite (Recommended for Quick Start)

```bash
cp local-env.sqlite.example local-env
```

**Features:**
- ✅ No database installation required
- ✅ Zero configuration
- ✅ Perfect for testing and development
- ✅ Database file: `C:\crypto-ia\crypto_test.db`

**Use When:**
- Getting started quickly
- Testing features
- Learning the application
- Don't need production-like environment

---

### Option 2: PostgreSQL (Recommended for Production-like Testing)

```bash
cp local-env.postgresql.example local-env
```

**Features:**
- ✅ Same database as production
- ✅ Better performance
- ✅ Full PostgreSQL features
- ✅ Tests real production behavior

**Use When:**
- Testing production scenarios
- Need better performance
- Want full PostgreSQL features
- Preparing for production deployment

**Requires:**
- PostgreSQL installation
- Database creation (see template for instructions)

---

## AWS Production

### Option 1: EC2 with PostgreSQL (Recommended for Small Deployments)

```bash
cp aws-env.ec2.example aws-env
```

**Features:**
- ✅ PostgreSQL on same EC2 instance
- ✅ Fully automated setup scripts
- ✅ Lower cost (~$15/month)
- ✅ Simpler architecture
- ✅ Automated backups via cron

**Use When:**
- Small to medium deployments
- Cost is a concern
- Simple architecture preferred
- Don't need high availability

**Setup:**
```bash
sudo ./remote-scripts/install-dependencies.sh
sudo ./remote-scripts/setup-postgresql.sh
sudo ./remote-scripts/setup-application.sh
```

---

### Option 2: EC2 with RDS (Recommended for Production)

```bash
cp aws-env.rds.example aws-env
```

**Features:**
- ✅ Managed PostgreSQL database (Amazon RDS)
- ✅ Automated backups and patching
- ✅ Multi-AZ high availability
- ✅ Better scalability
- ✅ CloudWatch monitoring
- ✅ Point-in-time recovery

**Use When:**
- Production deployments
- Need high availability
- Want managed database service
- Scaling is important
- Compliance requirements

**Cost:** ~$30-50/month (db.t3.small + storage)

**Setup:**
1. Create RDS instance in AWS Console
2. Deploy application to EC2
3. Configure aws-env with RDS endpoint
4. Run setup scripts (skip PostgreSQL setup)

---

## Quick Comparison

| Feature | SQLite | PostgreSQL (Local) | EC2 + PostgreSQL | EC2 + RDS |
|---------|--------|-------------------|------------------|-----------|
| **Setup Time** | 1 min | 10 min | 15 min | 30 min |
| **Cost** | Free | Free | ~$15/mo | ~$30-50/mo |
| **Database Install** | None | Manual | Automated | AWS Managed |
| **Performance** | Good | Excellent | Excellent | Excellent |
| **Scalability** | Low | Medium | Medium | High |
| **High Availability** | No | No | No | Yes (Multi-AZ) |
| **Backups** | Manual | Manual | Automated (cron) | Automated (AWS) |
| **Best For** | Development | Testing | Small prod | Production |

---

## Configuration Files Reference

```
crypto-ia/
├── local-env                          # Your local config (create this)
├── local-env.example                  # Points to templates below
├── local-env.sqlite.example          # ⭐ SQLite template
├── local-env.postgresql.example      # ⭐ PostgreSQL template
│
├── aws-env                            # Your AWS config (create this)
├── aws-env.example                    # Points to templates below
├── aws-env.ec2.example               # ⭐ EC2+PostgreSQL template
└── aws-env.rds.example               # ⭐ EC2+RDS template
```

---

## Getting Started

### For Development (Fastest):
```bash
cp local-env.sqlite.example local-env
nano local-env  # Add OPENAI_API_KEY
pip install -r requirements.txt
python start.py --all
```

### For Production-like Testing:
```bash
# Install PostgreSQL first
cp local-env.postgresql.example local-env
nano local-env  # Update DATABASE_URL and OPENAI_API_KEY
pip install -r requirements.txt
alembic upgrade head
python start.py --all
```

### For AWS Small Deployment:
```bash
# On EC2 instance
sudo ./remote-scripts/install-dependencies.sh
sudo ./remote-scripts/setup-postgresql.sh
cp aws-env.ec2.example aws-env
nano aws-env  # Update API keys
sudo ./remote-scripts/setup-application.sh
sudo ./remote-scripts/start-services.sh
```

### For AWS Production:
```bash
# Create RDS instance first, then on EC2:
sudo ./remote-scripts/install-dependencies.sh
cp aws-env.rds.example aws-env
nano aws-env  # Update RDS endpoint and API keys
sudo ./remote-scripts/setup-application.sh
source venv/bin/activate
alembic upgrade head
sudo ./remote-scripts/start-services.sh
```

---

## Need Help?

- **Configuration Guide**: See [docs/CONFIGURATION-GUIDE.md](docs/CONFIGURATION-GUIDE.md)
- **Local Deployment**: See [docs/LOCAL-DEPLOYMENT-GUIDE.md](docs/LOCAL-DEPLOYMENT-GUIDE.md)
- **AWS Deployment**: See [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)
- **Environment Path**: See [docs/ENVIRONMENT-PATH-GUIDE.md](docs/ENVIRONMENT-PATH-GUIDE.md)
