#!/bin/bash

# SnapStudy Frontend Build Script
# Simple script to build the React frontend

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔨 Building SnapStudy Frontend${NC}"
echo "==============================="

# Navigate to frontend directory
cd frontend

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
npm install

# Build the project
echo -e "${YELLOW}🏗️  Building production bundle...${NC}"
npm run build

echo -e "${GREEN}✅ Frontend build completed successfully!${NC}"
echo ""
echo -e "${BLUE}📁 Build files are located in: frontend/build/${NC}"
echo -e "${BLUE}🚀 Ready for deployment to S3${NC}"