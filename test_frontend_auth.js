#!/usr/bin/env node

/**
 * Test script to verify frontend authentication integration
 */

const axios = require('axios');

const API_BASE_URL = 'http://localhost:8000';

async function testAuthFlow() {
    console.log('🧪 Testing Frontend Authentication Flow...\n');

    try {
        // Test 1: Register a new user
        console.log('1️⃣ Testing user registration...');
        const registerData = {
            email: `test-${Date.now()}@example.com`,
            password: 'testpass123',
            first_name: 'Test',
            last_name: 'User'
        };

        const registerResponse = await axios.post(`${API_BASE_URL}/api/v1/auth/register`, registerData);
        console.log('✅ Registration successful');
        console.log('   - Access token received:', !!registerResponse.data.access_token);
        console.log('   - Refresh token received:', !!registerResponse.data.refresh_token);

        const { access_token, refresh_token } = registerResponse.data;

        // Test 2: Use access token to access protected endpoint
        console.log('\n2️⃣ Testing protected endpoint access...');
        const headers = { Authorization: `Bearer ${access_token}` };

        const onboardingData = {
            full_name: 'Test User',
            age: 25,
            profession: 'Developer',
            education_level: 'Bachelor',
            country: 'US',
            learning_style: 'visual',
            attention_span: 'medium',
            difficulty_level: 'intermediate'
        };

        const onboardingResponse = await axios.post(
            `${API_BASE_URL}/api/v1/users/onboarding`,
            onboardingData,
            { headers }
        );
        console.log('✅ Onboarding endpoint accessible');
        console.log('   - User updated:', !!onboardingResponse.data.user);
        console.log('   - Onboarding completed:', onboardingResponse.data.user.onboarding_completed);

        // Test 3: Test token refresh
        console.log('\n3️⃣ Testing token refresh...');
        const refreshResponse = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refresh_token
        });
        console.log('✅ Token refresh successful');
        console.log('   - New access token received:', !!refreshResponse.data.access_token);
        console.log('   - New refresh token received:', !!refreshResponse.data.refresh_token);

        // Test 4: Test login flow
        console.log('\n4️⃣ Testing login flow...');
        const loginResponse = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, {
            email: registerData.email,
            password: registerData.password
        });
        console.log('✅ Login successful');
        console.log('   - Access token received:', !!loginResponse.data.access_token);
        console.log('   - Refresh token received:', !!loginResponse.data.refresh_token);

        console.log('\n🎉 All authentication tests passed!');
        console.log('\n📋 Summary:');
        console.log('   ✅ User registration with tokens');
        console.log('   ✅ Protected endpoint access');
        console.log('   ✅ Token refresh mechanism');
        console.log('   ✅ User login flow');
        console.log('\n🚀 Frontend authentication integration is working correctly!');

    } catch (error) {
        console.error('\n❌ Authentication test failed:');
        if (error.response) {
            console.error('   Status:', error.response.status);
            console.error('   Data:', JSON.stringify(error.response.data, null, 2));
        } else {
            console.error('   Error:', error.message);
        }
        process.exit(1);
    }
}

// Run the test
testAuthFlow();