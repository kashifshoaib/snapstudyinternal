#!/usr/bin/env python3
"""
Migration script to update DynamoDB user table with missing fields.
This script adds missing fields to existing user records.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.src.services.dynamodb import db_service
from backend.src.config import settings

async def migrate_user_table():
    """
    Migrate existing user records to include all required fields.
    """
    print("🚀 Starting DynamoDB user table migration...")
    
    try:
        # Scan all users in the table
        response = db_service.users_table.scan()
        users = response.get('Items', [])
        
        print(f"📊 Found {len(users)} users to migrate")
        
        updated_count = 0
        
        for user in users:
            user_id = user.get('user_id')
            if not user_id:
                print(f"⚠️  Skipping user without user_id: {user}")
                continue
            
            # Prepare update fields with default values
            update_fields = {}
            
            # Add missing fields with default values
            if 'full_name' not in user:
                update_fields['full_name'] = None
            
            if 'age' not in user:
                update_fields['age'] = None
            
            if 'profession' not in user:
                update_fields['profession'] = None
            
            if 'education_level' not in user:
                update_fields['education_level'] = None
            
            if 'country' not in user:
                update_fields['country'] = None
            
            if 'learning_style' not in user:
                update_fields['learning_style'] = None
            
            if 'attention_span' not in user:
                update_fields['attention_span'] = None
            
            if 'difficulty_level' not in user:
                update_fields['difficulty_level'] = None
            
            if 'onboarding_completed' not in user:
                update_fields['onboarding_completed'] = False
            
            if 'preferences' not in user:
                update_fields['preferences'] = None
            
            if 'is_active' not in user:
                update_fields['is_active'] = True
            
            if 'created_at' not in user:
                update_fields['created_at'] = datetime.utcnow().isoformat()
            
            if 'updated_at' not in user:
                update_fields['updated_at'] = datetime.utcnow().isoformat()
            
            # Only update if there are missing fields
            if update_fields:
                try:
                    # Build update expression
                    update_expression = "SET "
                    expression_attribute_values = {}
                    
                    for i, (field, value) in enumerate(update_fields.items()):
                        if i > 0:
                            update_expression += ", "
                        update_expression += f"{field} = :{field}"
                        expression_attribute_values[f":{field}"] = value
                    
                    # Update the user record
                    db_service.users_table.update_item(
                        Key={'user_id': user_id},
                        UpdateExpression=update_expression,
                        ExpressionAttributeValues=expression_attribute_values
                    )
                    
                    updated_count += 1
                    print(f"✅ Updated user {user_id} with fields: {list(update_fields.keys())}")
                    
                except Exception as e:
                    print(f"❌ Failed to update user {user_id}: {str(e)}")
            else:
                print(f"✨ User {user_id} already has all required fields")
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"📈 Updated {updated_count} out of {len(users)} users")
        
    except Exception as e:
        print(f"💥 Migration failed: {str(e)}")
        raise

async def verify_migration():
    """
    Verify that the migration was successful by checking a few users.
    """
    print("\n🔍 Verifying migration...")
    
    try:
        # Get a sample of users to verify
        response = db_service.users_table.scan(Limit=5)
        users = response.get('Items', [])
        
        required_fields = [
            'user_id', 'email', 'full_name', 'age', 'profession', 
            'education_level', 'country', 'learning_style', 'attention_span',
            'difficulty_level', 'onboarding_completed', 'preferences',
            'created_at', 'updated_at', 'is_active'
        ]
        
        for user in users:
            user_id = user.get('user_id', 'Unknown')
            missing_fields = [field for field in required_fields if field not in user]
            
            if missing_fields:
                print(f"⚠️  User {user_id} still missing fields: {missing_fields}")
            else:
                print(f"✅ User {user_id} has all required fields")
        
        print("✨ Verification completed!")
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")

if __name__ == "__main__":
    print("🔧 DynamoDB User Table Migration Tool")
    print("=====================================")
    
    # Run migration
    asyncio.run(migrate_user_table())
    
    # Verify migration
    asyncio.run(verify_migration())
    
    print("\n🏁 Migration process completed!")