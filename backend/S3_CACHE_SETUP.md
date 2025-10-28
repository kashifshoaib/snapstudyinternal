# S3 Cache Bucket Setup

This document explains how the S3 cache bucket is managed in SnapStudy.

## Overview

The SnapStudy backend uses AWS S3 for caching lesson data (micro-lessons and quizzes). The cache bucket is automatically created and configured when the application starts up.

## Automatic Setup

The S3 cache bucket is automatically verified and created during application startup through the AWS health check system:

1. **On Application Startup**: The `startup_event()` in `main.py` calls `run_startup_aws_checks()`
2. **Health Check**: This runs `verify_s3_buckets()` which calls `s3_service.ensure_bucket_exists()`
3. **Bucket Creation**: If the bucket doesn't exist, it's automatically created with proper configuration

## Bucket Configuration

When created, the S3 bucket is configured with the following security and lifecycle settings:

### Security Settings
- **Encryption**: AES256 server-side encryption enabled
- **Versioning**: Enabled for data protection
- **Public Access**: Completely blocked (all 4 public access settings enabled)

### Lifecycle Policy
- **Cache Expiration**: Cache data (prefix: `cache/`) expires after 30 days
- **Version Cleanup**: Non-current versions are deleted after 7 days

## Manual Setup

If you need to manually ensure the S3 bucket exists before starting the application:

```bash
# From the backend directory
python scripts/setup_s3_cache.py
```

This script will:
1. Check if the bucket exists
2. Create it if it doesn't exist
3. Apply the proper configuration (encryption, versioning, lifecycle, public access blocking)
4. Display the results

## Configuration

The bucket name is configured via environment variables:

```bash
# .env file
CONTENT_BUCKET=snapstudy-content
AWS_REGION=us-east-1
AWS_PROFILE=your-profile  # Optional
```

## Cache Structure

Cached data is stored in S3 with the following structure:

```
s3://snapstudy-content/
├── cache/
│   └── lessons/
│       ├── {lesson_id}/
│       │   ├── micro_lessons.json
│       │   └── quiz.json
│       └── ...
└── uploads/
    └── {user_id}/
        └── ...
```

## Cache Operations

### Caching Lesson Data

```python
from src.services.s3 import s3_service

# Cache micro-lessons
await s3_service.cache_lesson_data(
    lesson_id="lesson-123",
    data_type="micro_lessons",
    data=micro_lessons_data
)

# Cache quiz data
await s3_service.cache_lesson_data(
    lesson_id="lesson-123",
    data_type="quiz",
    data=quiz_data
)
```

### Retrieving Cached Data

```python
# Get cached micro-lessons
cached_data = await s3_service.get_cached_lesson_data(
    lesson_id="lesson-123",
    data_type="micro_lessons"
)

if cached_data:
    print("Using cached data")
else:
    print("Cache miss - need to generate")
```

### Clearing Cache

```python
# Clear all cached data for a lesson
await s3_service.clear_lesson_cache(lesson_id="lesson-123")
```

## Required IAM Permissions

The AWS credentials used by the application need the following S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:HeadBucket",
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:PutBucketEncryption",
        "s3:PutBucketVersioning",
        "s3:PutPublicAccessBlock",
        "s3:PutLifecycleConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::snapstudy-content",
        "arn:aws:s3:::snapstudy-content/*"
      ]
    }
  ]
}
```

## Troubleshooting

### Bucket Creation Fails

If bucket creation fails during startup:

1. **Check Credentials**: Ensure AWS credentials are properly configured
2. **Check Permissions**: Verify IAM permissions listed above
3. **Bucket Name Conflict**: If the bucket name is taken, change `CONTENT_BUCKET` in `.env`
4. **Region Issues**: Ensure `AWS_REGION` is set correctly

### Cache Not Working

If caching doesn't work:

1. **Check Bucket Exists**: Run `python scripts/setup_s3_cache.py`
2. **Check Logs**: Look for S3 errors in application logs
3. **Check Permissions**: Ensure read/write permissions on the bucket
4. **Network Issues**: Verify connectivity to AWS S3 endpoints

## Monitoring

Check the health endpoint to see S3 bucket status:

```bash
curl http://localhost:8000/health
```

The response includes S3 bucket health information.

## Cost Optimization

The lifecycle policy automatically deletes:
- Cache data older than 30 days
- Non-current versions older than 7 days

This helps control S3 storage costs while maintaining reasonable cache retention.
