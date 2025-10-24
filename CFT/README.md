# SnapStudy Frontend Infrastructure

This directory contains CloudFormation templates and deployment scripts for the SnapStudy frontend infrastructure.

## What's Created

The CloudFormation template creates:

1. **S3 Bucket** (`aws-hackathon-snapstudy`)
   - Configured for static website hosting
   - Proper CORS settings
   - Public read access for web content

2. **CloudFront Distribution**
   - Global CDN for fast content delivery
   - HTTPS redirect enabled
   - Custom error pages for React Router support
   - Optimized caching policies

3. **Origin Access Control (OAC)**
   - Secure access from CloudFront to S3
   - Follows AWS security best practices

## Quick Deployment

### Option 1: Using the Deployment Script (Recommended)

```bash
cd CFT
./deploy-frontend.sh
```

### Option 2: Manual Deployment

1. **Build the frontend:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ../CFT
   ```

2. **Deploy the CloudFormation stack:**
   ```bash
   aws cloudformation deploy \
     --template-file frontend-infrastructure.yaml \
     --stack-name snapstudy-frontend \
     --parameter-overrides BucketName=aws-hackathon-snapstudy \
     --capabilities CAPABILITY_IAM
   ```

3. **Upload your frontend files:**
   ```bash
   aws s3 sync ../frontend/build/ s3://aws-hackathon-snapstudy/ --delete
   ```

3. **Get your CloudFront URL:**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name snapstudy-frontend \
     --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
     --output text
   ```

## Prerequisites

- AWS CLI installed and configured
- Node.js and npm installed (for building the frontend)
- Appropriate AWS permissions for CloudFormation, S3, and CloudFront

**Note:** The frontend build directory is not included in the repository. The deployment script will automatically build the frontend if needed.

## Configuration

### Bucket Name
The default bucket name is `aws-hackathon-snapstudy`. You can change it by:

1. **Via parameter:**
   ```bash
   aws cloudformation deploy \
     --template-file frontend-infrastructure.yaml \
     --stack-name snapstudy-frontend \
     --parameter-overrides BucketName=your-custom-bucket-name
   ```

2. **Edit the template:** Change the `Default` value in the `BucketName` parameter

### Custom Domain (Optional)

To use a custom domain:

1. Add your SSL certificate ARN to the template
2. Update the `ViewerCertificate` section
3. Add your domain to `Aliases` in the CloudFront distribution
4. Create a Route 53 record pointing to the CloudFront distribution

## Updating Your Frontend

After making changes to your React app:

1. **Rebuild:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Upload to S3:**
   ```bash
   aws s3 sync frontend/build/ s3://aws-hackathon-snapstudy/ --delete
   ```

3. **Invalidate CloudFront cache:**
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id YOUR_DISTRIBUTION_ID \
     --paths "/*"
   ```

## Stack Outputs

The CloudFormation stack provides these outputs:

- `BucketName`: S3 bucket name
- `BucketWebsiteURL`: Direct S3 website URL
- `CloudFrontDistributionId`: CloudFront distribution ID
- `CloudFrontDomainName`: CloudFront domain name
- `CloudFrontURL`: Full HTTPS URL to access your app
- `DeploymentInstructions`: Quick reference commands

## Security Features

- **HTTPS Only**: CloudFront redirects HTTP to HTTPS
- **Origin Access Control**: Secure S3 access via CloudFront
- **CORS Enabled**: Proper CORS headers for API calls
- **Public Read**: S3 objects are publicly readable for web hosting

## Cost Optimization

- **Price Class 100**: Uses only North America and Europe edge locations
- **Efficient Caching**: Static assets cached for 1 year, HTML files not cached
- **Compression**: Gzip compression enabled for faster loading

## Troubleshooting

### Common Issues

1. **Bucket name already exists**: Change the `BucketName` parameter
2. **Access denied**: Check AWS credentials and permissions
3. **404 errors**: Ensure `index.html` exists in your build directory
4. **React Router not working**: The template includes custom error pages for SPA support

### Useful Commands

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name snapstudy-frontend

# List S3 bucket contents
aws s3 ls s3://aws-hackathon-snapstudy/

# Check CloudFront distribution status
aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID

# View CloudFront logs (if enabled)
aws logs describe-log-groups --log-group-name-prefix /aws/cloudfront/
```