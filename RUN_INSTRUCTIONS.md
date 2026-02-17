# 🚀 RunPrayers API - How to Run

## Quick Start

### 1. **Start the FastAPI Server**
```bash
# Run the modern async FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or for production (no reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. **Access the Application**
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Root Endpoint**: http://localhost:8000/

## 📋 Available API Endpoints

### **Add Prayer**
```bash
# Add a new prayer request
curl -X POST "http://localhost:8000/api/add_prayer" \
  -H "Content-Type: application/json" \
  -d '{
    "prayer_name": "John Doe",
    "request": "למציאת עבודה טובה",
    "phone": "050-1234567",
    "contact_name": "John",
    "tag_contact": true,
    "target_list": "default"
  }'
```

### **Send Prayer Email**
```bash
# Send the next prayer via email
curl -X POST "http://localhost:8000/api/send_prayer?recipient=your-email@example.com"
```

### **Preview Next Prayer**
```bash
# Get next prayer without sending email
curl -X GET "http://localhost:8000/api/next_prayer"
```

### **Get Statistics**
```bash
# View prayer statistics and service status
curl -X GET "http://localhost:8000/api/stats"
```

### **Health Check**
```bash
# Check service health
curl -X GET "http://localhost:8000/api/health"
```

## 🛠️ Environment Setup

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Configure Environment Variables**
Copy `.env.template` to `.env` and fill in your credentials:

```bash
# Copy template
cp .env.template .env

# Edit with your actual values
# SENDER_EMAIL=your-gmail@gmail.com
# SENDER_PASSWORD=your-app-password
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-service-key
```

### **3. Data Mode Configuration**
Set your preferred data storage mode in `.env`:

```bash
# For Supabase database (recommended for production)
DATA_MODE=database

# For local JSON files (good for development/testing)
DATA_MODE=local
```

## 🔧 Development Mode

### **Run with Hot Reload**
```bash
uvicorn app.main:app --reload --log-level info
```

### **Run Tests**
```bash
pytest tests/ -v
```

### **Check Service Status**
```bash
# Quick health check
curl http://localhost:8000/ping

# Detailed health check
curl http://localhost:8000/api/health
```

## 🚀 Production Deployment

### **Render.com**
The application is ready for Render deployment:

1. **Connect your repository** to Render
2. **Set environment variables** in Render dashboard
3. **Deploy command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### **Docker**
```dockerfile
# Use the application with Docker
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY .env .env

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## ❌ What NOT to Use Anymore

The following old commands **no longer work** after our refactoring:

```bash
# ❌ OLD - Don't use these anymore:
python -m prayer_logic.prayers_file --target-list default
python app.py
python prayers_file_new2.py

# ✅ NEW - Use this instead:
uvicorn app.main:app --reload
```

## 🔄 Migration from Old Version

If you have existing data in local JSON files, they should automatically work with the new system since we maintained backward compatibility for the local storage format.

## 📊 Monitoring

### **Service Health**
```bash
# Check if everything is working
curl -s http://localhost:8000/api/health | jq
```

### **View Logs**
The application provides structured logging. Watch logs during development:

```bash
uvicorn app.main:app --log-level debug
```

## 🆘 Troubleshooting

### **Common Issues:**

1. **Import Errors**: Make sure you're in the project directory and dependencies are installed
2. **Environment Variables**: Check that `.env` file exists and contains all required values
3. **Port Already in Use**: Change port with `--port 8001`
4. **Database Connection**: Check Supabase credentials or switch to `DATA_MODE=local`

### **Get Help:**
```bash
# Check service status
curl http://localhost:8000/api/health

# View detailed stats
curl http://localhost:8000/api/stats
```

---

**The new architecture is much more robust, async-first, and production-ready! 🎉**