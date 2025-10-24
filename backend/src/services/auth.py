"""
Authentication service for SnapStudy using AWS Cognito.

Provides secure user authentication, registration, and token management
using AWS Cognito User Pools with SRP (Secure Remote Password) authentication.
"""

import boto3
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from ..config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Service for user authentication using AWS Cognito."""

    def __init__(self):
        self.cognito_client = boto3.client('cognito-idp', region_name=settings.aws_region)
        self.user_pool_id = settings.user_pool_id
        self.client_id = settings.user_pool_client_id
        self.client_secret = getattr(settings, 'user_pool_client_secret', None)

    def _get_secret_hash(self, username: str) -> Optional[str]:
        """
        Calculate secret hash for Cognito if client secret is configured.

        Args:
            username: Username or email

        Returns:
            Secret hash or None if no client secret
        """
        if not self.client_secret:
            return None

        message = bytes(username + self.client_id, 'utf-8')
        secret = bytes(self.client_secret, 'utf-8')
        dig = hmac.new(secret, msg=message, digestmod=hashlib.sha256).digest()
        return base64.b64encode(dig).decode()

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with Cognito using ADMIN_NO_SRP_AUTH flow.

        This is a server-side authentication flow suitable for backend services.
        For client-side apps, use USER_SRP_AUTH instead.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Dict containing user info and tokens

        Raises:
            HTTPException: On authentication failure
        """
        try:
            # Prepare auth parameters
            auth_params = {
                'USERNAME': email,
                'PASSWORD': password
            }

            # Add secret hash if configured
            secret_hash = self._get_secret_hash(email)
            if secret_hash:
                auth_params['SECRET_HASH'] = secret_hash

            # Initiate admin authentication
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters=auth_params
            )

            # Check for challenges
            if 'ChallengeName' in response:
                challenge_name = response['ChallengeName']

                if challenge_name == 'NEW_PASSWORD_REQUIRED':
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            'error': 'NEW_PASSWORD_REQUIRED',
                            'message': 'New password required for first login',
                            'session': response['Session']
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Authentication challenge required: {challenge_name}"
                    )

            # Extract tokens
            auth_result = response['AuthenticationResult']

            # Get user attributes
            user_info = await self._get_user_info(auth_result['AccessToken'])

            logger.info(f"User {email} authenticated successfully")

            return {
                'user_id': user_info['sub'],
                'email': user_info['email'],
                'full_name': user_info.get('name', ''),
                'access_token': auth_result['AccessToken'],
                'refresh_token': auth_result.get('RefreshToken'),
                'id_token': auth_result['IdToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': auth_result['TokenType'],
                'authenticated_at': datetime.utcnow().isoformat()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            logger.error(f"Cognito authentication error: {error_code} - {error_message}")

            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password"
                )
            elif error_code == 'UserNotFoundException':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            elif error_code == 'UserNotConfirmedException':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User email not verified. Please verify your email."
                )
            elif error_code == 'TooManyRequestsException':
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many authentication attempts. Please try again later."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Authentication service error: {error_message}"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed due to unexpected error"
            )

    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user in Cognito.

        Args:
            user_data: Dict containing user registration data
                - email: User's email (required)
                - password: User's password (required)
                - full_name: User's full name (optional)
                - profession: User's profession (optional)
                - learning_style: Preferred learning style (optional)
                - education_level: Education level (optional)

        Returns:
            Dict containing registration result

        Raises:
            HTTPException: On registration failure
        """
        try:
            email = user_data.get('email')
            password = user_data.get('password')

            if not email or not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email and password are required"
                )

            # Prepare user attributes
            user_attributes = [
                {'Name': 'email', 'Value': email}
            ]

            # Add optional attributes
            if user_data.get('full_name'):
                user_attributes.append({'Name': 'name', 'Value': user_data['full_name']})

            # Add custom attributes
            custom_attrs = {
                'profession': user_data.get('profession', ''),
                'learning_style': user_data.get('learning_style', 'visual'),
                'education_level': user_data.get('education_level', 'college'),
                'difficulty_level': user_data.get('difficulty_level', 'intermediate'),
                'country': user_data.get('country', 'US')
            }

            for attr_name, attr_value in custom_attrs.items():
                if attr_value:
                    user_attributes.append({
                        'Name': f'custom:{attr_name}',
                        'Value': str(attr_value)
                    })

            # Prepare sign up parameters
            signup_params = {
                'ClientId': self.client_id,
                'Username': email,
                'Password': password,
                'UserAttributes': user_attributes
            }

            # Add secret hash if configured
            secret_hash = self._get_secret_hash(email)
            if secret_hash:
                signup_params['SecretHash'] = secret_hash

            # Sign up user
            response = self.cognito_client.sign_up(**signup_params)

            logger.info(f"User {email} registered successfully")

            # If auto-confirm is disabled, user needs to verify email
            confirmation_required = not response['UserConfirmed']

            return {
                'user_id': response['UserSub'],
                'email': email,
                'confirmed': response['UserConfirmed'],
                'confirmation_required': confirmation_required,
                'message': 'User registered successfully. Please verify your email.' if confirmation_required else 'User registered and confirmed.',
                'registration_timestamp': datetime.utcnow().isoformat()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            logger.error(f"Cognito registration error: {error_code} - {error_message}")

            if error_code == 'UsernameExistsException':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists"
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password does not meet requirements: minimum 8 characters, must contain uppercase, lowercase, and numbers"
                )
            elif error_code == 'InvalidParameterException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid registration data: {error_message}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Registration service error: {error_message}"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected registration error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed due to unexpected error"
            )

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT access token from Cognito.

        Args:
            token: Access token to verify

        Returns:
            Dict containing user info if valid, None if invalid
        """
        try:
            # Get user info from access token
            user_info = await self._get_user_info(token)

            return {
                'user_id': user_info['sub'],
                'email': user_info['email'],
                'username': user_info.get('cognito:username', user_info['email']),
                'email_verified': user_info.get('email_verified', False),
                'attributes': user_info
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NotAuthorizedException':
                logger.warning("Invalid or expired token")
                return None
            else:
                logger.error(f"Token verification error: {error_code}")
                return None
        except Exception as e:
            logger.error(f"Unexpected token verification error: {str(e)}")
            return None

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from initial authentication

        Returns:
            Dict containing new tokens

        Raises:
            HTTPException: On refresh failure
        """
        try:
            # Prepare auth parameters
            auth_params = {
                'REFRESH_TOKEN': refresh_token
            }

            # Get username from refresh token for secret hash
            # Note: In production, you'd want to store this mapping
            # For now, we'll proceed without secret hash for refresh

            response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters=auth_params
            )

            auth_result = response['AuthenticationResult']

            logger.info("Token refreshed successfully")

            return {
                'access_token': auth_result['AccessToken'],
                'id_token': auth_result['IdToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': auth_result['TokenType'],
                'refreshed_at': datetime.utcnow().isoformat()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Token refresh error: {error_code}")

            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token. Please login again."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unable to refresh token"
                )
        except Exception as e:
            logger.error(f"Unexpected token refresh error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )

    async def confirm_email(self, email: str, confirmation_code: str) -> Dict[str, Any]:
        """
        Confirm user email with verification code.

        Args:
            email: User's email
            confirmation_code: Verification code sent to email

        Returns:
            Dict containing confirmation result

        Raises:
            HTTPException: On confirmation failure
        """
        try:
            # Prepare parameters
            confirm_params = {
                'ClientId': self.client_id,
                'Username': email,
                'ConfirmationCode': confirmation_code
            }

            # Add secret hash if configured
            secret_hash = self._get_secret_hash(email)
            if secret_hash:
                confirm_params['SecretHash'] = secret_hash

            self.cognito_client.confirm_sign_up(**confirm_params)

            logger.info(f"Email confirmed for user {email}")

            return {
                'success': True,
                'email': email,
                'message': 'Email verified successfully. You can now login.',
                'confirmed_at': datetime.utcnow().isoformat()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Email confirmation error: {error_code}")

            if error_code == 'CodeMismatchException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification code"
                )
            elif error_code == 'ExpiredCodeException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code expired. Please request a new code."
                )
            elif error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already confirmed or invalid state"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Email verification failed"
                )
        except Exception as e:
            logger.error(f"Unexpected email confirmation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Email verification failed"
            )

    async def resend_confirmation_code(self, email: str) -> Dict[str, Any]:
        """
        Resend email verification code.

        Args:
            email: User's email

        Returns:
            Dict containing result

        Raises:
            HTTPException: On failure
        """
        try:
            # Prepare parameters
            resend_params = {
                'ClientId': self.client_id,
                'Username': email
            }

            # Add secret hash if configured
            secret_hash = self._get_secret_hash(email)
            if secret_hash:
                resend_params['SecretHash'] = secret_hash

            response = self.cognito_client.resend_confirmation_code(**resend_params)

            logger.info(f"Confirmation code resent to {email}")

            return {
                'success': True,
                'email': email,
                'delivery_medium': response['CodeDeliveryDetails']['DeliveryMedium'],
                'destination': response['CodeDeliveryDetails']['Destination'],
                'message': 'Verification code sent to your email'
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Resend confirmation error: {error_code}")

            if error_code == 'UserNotFoundException':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            elif error_code == 'InvalidParameterException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already confirmed"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to resend verification code"
                )

    async def forgot_password(self, email: str) -> Dict[str, Any]:
        """
        Initiate forgot password flow.

        Args:
            email: User's email

        Returns:
            Dict containing result

        Raises:
            HTTPException: On failure
        """
        try:
            # Prepare parameters
            forgot_params = {
                'ClientId': self.client_id,
                'Username': email
            }

            # Add secret hash if configured
            secret_hash = self._get_secret_hash(email)
            if secret_hash:
                forgot_params['SecretHash'] = secret_hash

            response = self.cognito_client.forgot_password(**forgot_params)

            logger.info(f"Password reset initiated for {email}")

            return {
                'success': True,
                'email': email,
                'delivery_medium': response['CodeDeliveryDetails']['DeliveryMedium'],
                'destination': response['CodeDeliveryDetails']['Destination'],
                'message': 'Password reset code sent to your email'
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Forgot password error: {error_code}")

            if error_code == 'UserNotFoundException':
                # For security, don't reveal if user exists
                return {
                    'success': True,
                    'email': email,
                    'message': 'If an account exists, a reset code has been sent'
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initiate password reset"
                )

    async def confirm_forgot_password(
        self,
        email: str,
        confirmation_code: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Confirm forgot password with code and set new password.

        Args:
            email: User's email
            confirmation_code: Reset code from email
            new_password: New password

        Returns:
            Dict containing result

        Raises:
            HTTPException: On failure
        """
        try:
            # Prepare parameters
            confirm_params = {
                'ClientId': self.client_id,
                'Username': email,
                'ConfirmationCode': confirmation_code,
                'Password': new_password
            }

            # Add secret hash if configured
            secret_hash = self._get_secret_hash(email)
            if secret_hash:
                confirm_params['SecretHash'] = secret_hash

            self.cognito_client.confirm_forgot_password(**confirm_params)

            logger.info(f"Password reset completed for {email}")

            return {
                'success': True,
                'email': email,
                'message': 'Password reset successfully. You can now login with your new password.',
                'reset_at': datetime.utcnow().isoformat()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Confirm forgot password error: {error_code}")

            if error_code == 'CodeMismatchException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid reset code"
                )
            elif error_code == 'ExpiredCodeException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reset code expired. Please request a new code."
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password does not meet requirements"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Password reset failed"
                )

    async def logout(self, access_token: str) -> Dict[str, Any]:
        """
        Sign out user (invalidate tokens globally).

        Args:
            access_token: User's access token

        Returns:
            Dict containing result
        """
        try:
            self.cognito_client.global_sign_out(
                AccessToken=access_token
            )

            logger.info("User logged out successfully")

            return {
                'success': True,
                'message': 'Logged out successfully',
                'logged_out_at': datetime.utcnow().isoformat()
            }

        except ClientError as e:
            logger.error(f"Logout error: {e}")
            # Don't fail logout even if Cognito call fails
            return {
                'success': True,
                'message': 'Logged out (local only)',
                'logged_out_at': datetime.utcnow().isoformat()
            }

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from access token.

        Args:
            access_token: Cognito access token

        Returns:
            Dict containing user attributes
        """
        response = self.cognito_client.get_user(
            AccessToken=access_token
        )

        # Convert attribute list to dict
        user_attributes = {
            attr['Name']: attr['Value']
            for attr in response['UserAttributes']
        }

        return user_attributes


# Global service instance
auth_service = AuthService()
