# RunPrayers Deployment Guide for Render.com

This guide provides step-by-step instructions for deploying the RunPrayers FastAPI application to Render.com with automated daily prayer emails.

## Prerequisites

- GitHub account with your project repository
- Render.com account
- Supabase account with database setup
- Gmail account with app-specific password configured

## 1. Environment Configuration

### Required Environment Variables

Copy these environment variables to your Render service:

```bash
# Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Email Configuration
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your-app-specific-password

# Application Settings
DEFAULT_RECIPIENT=recipient@example.com
ENVIRONMENT=production

# Optional: For cron job recipient override
CRON_RECIPIENT=daily-prayer@example.com
```

### Setting up Gmail App Password

1. Enable 2-factor authentication on your Gmail account
2. Go to Google Account settings
3. Navigate to Security → App passwords
4. Generate an app password for "Mail"
5. Use this password (not your regular password) for `GMAIL_APP_PASSWORD`

## 2. Render.com Deployment

### Step 1: Connect Repository

1. Log in to [Render.com](https://render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository containing this project
4. Select the repository and branch (usually `main` or `master`)

### Step 2: Configure Web Service

**Basic Settings:**
- **Name:** `runprayers-api` (or your preferred name)
- **Environment:** `Python 3`
- **Region:** Choose closest to your users
- **Branch:** `main`

**Build & Deploy:**
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `./start.sh`

**Advanced Settings:**
- **Auto-Deploy:** Yes (recommended)

### Step 3: Add Environment Variables

In your Render service dashboard:

1. Go to "Environment" tab
2. Add all required environment variables listed above
3. Click "Save Changes"

### Step 4: Configure Cron Job

1. In your Render dashboard, click "New" → "Cron Job"
2. **Name:** `daily-prayer-sender`
3. **Environment:** `Python 3`
4. **Command:** `python scripts/daily_prayer_cron.py`
5. **Schedule:** `0 9 * * *` (9 AM daily, adjust timezone as needed)
6. Connect to the same GitHub repository
7. Add the same environment variables as your web service

## 3. Verification Steps

### Step 1: Check Web Service Health

After deployment, verify your service is running:

```bash
curl https://your-app-name.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T09:00:00Z",
  "components": {
    "configuration": "healthy",
    "prayer_service": "healthy",
    "database": "healthy",
    "email_config": "healthy"
  }
}
```

### Step 2: Test Prayer API

```bash
# Get prayer status
curl https://your-app-name.onrender.com/api/prayers/status

# Send a test prayer (POST request)
curl -X POST https://your-app-name.onrender.com/api/prayers/send \
  -H "Content-Type: application/json" \
  -d '{"recipient": "test@example.com"}'
```

### Step 3: Verify Cron Job

1. Check cron job logs in Render dashboard
2. Confirm daily prayer emails are being sent
3. Monitor the health check endpoint

## 4. Monitoring and Troubleshooting

### Health Monitoring

The application includes a health check endpoint at `/health` that monitors:
- Configuration validity
- Prayer service status
- Database connectivity
- Email configuration

### Log Monitoring

**Web Service Logs:**
- Access via Render dashboard → Your Service → Logs
- Shows API requests, errors, and startup information

**Cron Job Logs:**
- Access via Render dashboard → Your Cron Job → Logs
- Shows daily prayer sending results and any errors

### Common Issues

**1. Service Won't Start**
- Check environment variables are set correctly
- Verify `start.sh` has execution permissions
- Review build logs for dependency issues

**2. Database Connection Errors**
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check Supabase service status
- Ensure database tables exist

**3. Email Sending Failures**
- Verify Gmail app password is correct
- Check Gmail account security settings
- Ensure 2FA is enabled and app password is generated

**4. Cron Job Not Running**
- Check cron schedule syntax
- Verify environment variables are set for cron job
- Review cron job logs for errors

### Performance Optimization

**Connection Pooling:**
- The application uses async connection pooling for better performance
- Monitor connection usage in logs

**Scaling:**
- Render automatically handles scaling
- Monitor response times and adjust instance type if needed

## 5. Maintenance

### Updating the Application

1. Push changes to your GitHub repository
2. Render will automatically redeploy (if auto-deploy is enabled)
3. Monitor deployment logs for any issues
4. Verify health check passes after deployment

### Database Maintenance

- Regularly backup your Supabase database
- Monitor prayer data growth
- Consider data archiving for old prayers if needed

### Security

- Regularly rotate Gmail app passwords
- Monitor access logs
- Keep dependencies updated via Dependabot

## 6. Scaling Considerations

**For Higher Volume:**
- Upgrade Render plan for more resources
- Consider implementing prayer sending queues
- Add rate limiting for API endpoints
- Implement caching for prayer data

**For Multiple Time Zones:**
- Create multiple cron jobs for different time zones
- Add timezone configuration to user profiles
- Consider using Render's regional deployments

## Support

For issues specific to this deployment:
1. Check the logs in Render dashboard
2. Verify health check endpoint
3. Review this guide for configuration steps

For Render.com specific issues:
- [Render Documentation](https://docs.render.com/)
- [Render Support](https://render.com/support)

---

**Note:** This application is designed to be stateless and ephemeral-filesystem ready, making it perfect for Render's infrastructure.