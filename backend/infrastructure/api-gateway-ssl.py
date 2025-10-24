"""
API Gateway with SSL configuration for SnapStudy backend.
This provides HTTPS endpoint that proxies to HTTP Elastic Beanstalk.
"""

from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    CfnOutput
)
from constructs import Construct

class ApiGatewaySSLStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Your Elastic Beanstalk URL
        backend_url = "snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com"
        
        # Create API Gateway with HTTP integration to Elastic Beanstalk
        api = apigateway.RestApi(
            self, "SnapStudyAPI",
            rest_api_name="SnapStudy Backend API",
            description="HTTPS API Gateway proxy to Elastic Beanstalk backend",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],  # Restrict in production
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["*"]
            ),
            binary_media_types=["*/*"]  # Support file uploads
        )
        
        # Create HTTP integration to Elastic Beanstalk
        integration = apigateway.HttpIntegration(
            f"http://{backend_url}/{{proxy}}",
            http_method="ANY",
            options=apigateway.IntegrationOptions(
                request_parameters={
                    "integration.request.path.proxy": "method.request.path.proxy"
                }
            )
        )
        
        # Add proxy resource to handle all paths
        proxy_resource = api.root.add_resource("{proxy+}")
        proxy_resource.add_method(
            "ANY", 
            integration,
            request_parameters={
                "method.request.path.proxy": True
            }
        )
        
        # Also handle root path
        api.root.add_method("ANY", integration)
        
        # Output the API Gateway URL
        CfnOutput(
            self, "ApiGatewayUrl",
            value=api.url,
            description="HTTPS API Gateway URL",
            export_name="SnapStudy-ApiGatewayUrl"
        )

# Optional: Custom domain configuration
class CustomDomainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, domain_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get hosted zone (you need to have a domain in Route53)
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=domain_name
        )
        
        # Create SSL certificate
        certificate = acm.Certificate(
            self, "Certificate",
            domain_name=f"api.{domain_name}",
            validation=acm.CertificateValidation.from_dns(hosted_zone)
        )
        
        # Create API Gateway with custom domain
        api = apigateway.RestApi(
            self, "SnapStudyAPI",
            rest_api_name="SnapStudy Backend API",
            domain_name=apigateway.DomainNameOptions(
                domain_name=f"api.{domain_name}",
                certificate=certificate
            )
        )
        
        # Create Route53 record
        route53.ARecord(
            self, "ApiRecord",
            zone=hosted_zone,
            record_name="api",
            target=route53.RecordTarget.from_alias(
                targets.ApiGateway(api)
            )
        )