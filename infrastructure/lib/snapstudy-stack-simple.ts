import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as sfnTasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import { Construct } from 'constructs';

export class SnapStudyStack extends cdk.Stack {
  public usersTable: dynamodb.Table;
  public lessonsTable: dynamodb.Table;
  public microLessonsTable: dynamodb.Table;
  public quizzesTable: dynamodb.Table;
  public userEngagementTable: dynamodb.Table;
  public chatHistoryTable: dynamodb.Table;
  public audioLessonsTable: dynamodb.Table;
  public videoLessonsTable: dynamodb.Table;
  public contentBucket: s3.Bucket;
  public userPool: cognito.UserPool;
  public userPoolClient: cognito.UserPoolClient;
  public restApi: apigateway.RestApi;
  public mainApiFunction: lambda.Function;
  public contentProcessorFunction: lambda.Function;
  public multimediaProcessorFunction: lambda.Function;
  public contentProcessingQueue: sqs.Queue;
  public multimediaProcessingQueue: sqs.Queue;
  public contentProcessingTopic: sns.Topic;
  public distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create DynamoDB Tables
    this.createDynamoDBTables();
    
    // Create S3 Bucket for content storage
    this.createS3Bucket();
    
    // Create SQS Queues for processing
    this.createSQSQueues();
    
    // Create SNS Topics for notifications
    this.createSNSTopics();
    
    // Create Lambda Functions
    this.createLambdaFunctions();
    
    // Create Cognito User Pool and Identity Pool
    this.createCognitoResources();
    
    // Create API Gateway
    this.createApiGateway();
    
    // Create CloudFront Distribution
    this.createCloudFrontDistribution();
    
    // Create CloudWatch Resources
    this.createCloudWatchResources();
    
    // Create IAM roles and policies
    this.createIAMRoles();
    
    // Output important values
    this.createOutputs();
  }

  private createDynamoDBTables() {
    // Users Table
    this.usersTable = new dynamodb.Table(this, 'UsersTable', {
      tableName: 'SnapStudy-Users',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });

    // Add GSI for email lookup
    this.usersTable.addGlobalSecondaryIndex({
      indexName: 'EmailIndex',
      partitionKey: {
        name: 'email',
        type: dynamodb.AttributeType.STRING
      }
    });

    // Lessons Table
    this.lessonsTable = new dynamodb.Table(this, 'LessonsTable', {
      tableName: 'SnapStudy-Lessons',
      partitionKey: {
        name: 'lesson_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });

    // Add GSI for user lessons lookup
    this.lessonsTable.addGlobalSecondaryIndex({
      indexName: 'UserLessonsIndex',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING
      }
    });

    // MicroLessons Table
    this.microLessonsTable = new dynamodb.Table(this, 'MicroLessonsTable', {
      tableName: 'SnapStudy-MicroLessons',
      partitionKey: {
        name: 'micro_lesson_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });

    // Add GSI for lesson micro-lessons lookup
    this.microLessonsTable.addGlobalSecondaryIndex({
      indexName: 'LessonMicroLessonsIndex',
      partitionKey: {
        name: 'lesson_id',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'sequence_number',
        type: dynamodb.AttributeType.NUMBER
      }
    });

    // Quizzes Table
    this.quizzesTable = new dynamodb.Table(this, 'QuizzesTable', {
      tableName: 'SnapStudy-Quizzes',
      partitionKey: {
        name: 'quiz_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });

    // Add GSI for micro-lesson quizzes lookup
    this.quizzesTable.addGlobalSecondaryIndex({
      indexName: 'MicroLessonQuizzesIndex',
      partitionKey: {
        name: 'micro_lesson_id',
        type: dynamodb.AttributeType.STRING
      }
    });

    // UserEngagement Table
    this.userEngagementTable = new dynamodb.Table(this, 'UserEngagementTable', {
      tableName: 'SnapStudy-UserEngagement',
      partitionKey: {
        name: 'engagement_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      timeToLiveAttribute: 'ttl'
    });

    // Add GSI for user analytics
    this.userEngagementTable.addGlobalSecondaryIndex({
      indexName: 'UserEngagementIndex',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.STRING
      }
    });

    // ChatHistory Table
    this.chatHistoryTable = new dynamodb.Table(this, 'ChatHistoryTable', {
      tableName: 'SnapStudy-ChatHistory',
      partitionKey: {
        name: 'session_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      timeToLiveAttribute: 'ttl'
    });

    // AudioLessons Table
    this.audioLessonsTable = new dynamodb.Table(this, 'AudioLessonsTable', {
      tableName: 'SnapStudy-AudioLessons',
      partitionKey: {
        name: 'audio_lesson_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });

    // VideoLessons Table
    this.videoLessonsTable = new dynamodb.Table(this, 'VideoLessonsTable', {
      tableName: 'SnapStudy-VideoLessons',
      partitionKey: {
        name: 'video_lesson_id',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: dynamodb.TableEncryption.AWS_MANAGED
    });
  }

  private createS3Bucket() {
    this.contentBucket = new s3.Bucket(this, 'ContentBucket', {
      bucketName: `snapstudy-content-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });
  }

  private createSQSQueues() {
    // Content Processing Queue
    this.contentProcessingQueue = new sqs.Queue(this, 'ContentProcessingQueue', {
      queueName: 'snapstudy-content-processing',
      visibilityTimeout: cdk.Duration.minutes(15),
      retentionPeriod: cdk.Duration.days(14)
    });

    // Multimedia Processing Queue
    this.multimediaProcessingQueue = new sqs.Queue(this, 'MultimediaProcessingQueue', {
      queueName: 'snapstudy-multimedia-processing',
      visibilityTimeout: cdk.Duration.minutes(15),
      retentionPeriod: cdk.Duration.days(14)
    });
  }

  private createSNSTopics() {
    // Content Processing Topic
    this.contentProcessingTopic = new sns.Topic(this, 'ContentProcessingTopic', {
      topicName: 'snapstudy-content-processing',
      displayName: 'SnapStudy Content Processing Notifications'
    });

    // Subscribe SQS queue to SNS topic
    this.contentProcessingTopic.addSubscription(
      new snsSubscriptions.SqsSubscription(this.contentProcessingQueue)
    );
  }

  private createLambdaFunctions() {
    // Main API Function
    this.mainApiFunction = new lambda.Function(this, 'MainApiFunction', {
      functionName: 'snapstudy-api',
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: 'lambda_functions.main_handler.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024,
      environment: {
        ENVIRONMENT: 'production',
        USERS_TABLE: this.usersTable.tableName,
        LESSONS_TABLE: this.lessonsTable.tableName,
        MICRO_LESSONS_TABLE: this.microLessonsTable.tableName,
        QUIZZES_TABLE: this.quizzesTable.tableName,
        USER_ENGAGEMENT_TABLE: this.userEngagementTable.tableName,
        CHAT_HISTORY_TABLE: this.chatHistoryTable.tableName,
        AUDIO_LESSONS_TABLE: this.audioLessonsTable.tableName,
        VIDEO_LESSONS_TABLE: this.videoLessonsTable.tableName,
        CONTENT_BUCKET: this.contentBucket.bucketName,
        USER_POOL_ID: this.userPool.userPoolId,
        USER_POOL_CLIENT_ID: this.userPoolClient.userPoolClientId
      }
    });

    // Content Processor Function
    this.contentProcessorFunction = new lambda.Function(this, 'ContentProcessorFunction', {
      functionName: 'snapstudy-content-processor',
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: 'lambda_functions.content_processor.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048,
      environment: {
        ENVIRONMENT: 'production',
        USERS_TABLE: this.usersTable.tableName,
        LESSONS_TABLE: this.lessonsTable.tableName,
        MICRO_LESSONS_TABLE: this.microLessonsTable.tableName,
        CONTENT_BUCKET: this.contentBucket.bucketName
      }
    });

    // Multimedia Processor Function
    this.multimediaProcessorFunction = new lambda.Function(this, 'MultimediaProcessorFunction', {
      functionName: 'snapstudy-multimedia-processor',
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: 'lambda_functions.multimedia_processor.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 3008,
      environment: {
        ENVIRONMENT: 'production',
        LESSONS_TABLE: this.lessonsTable.tableName,
        AUDIO_LESSONS_TABLE: this.audioLessonsTable.tableName,
        VIDEO_LESSONS_TABLE: this.videoLessonsTable.tableName,
        CONTENT_BUCKET: this.contentBucket.bucketName
      }
    });

    // Add event sources to Lambda functions
    this.contentProcessorFunction.addEventSource(
      new lambdaEventSources.SqsEventSource(this.contentProcessingQueue, {
        batchSize: 1
      })
    );

    this.multimediaProcessorFunction.addEventSource(
      new lambdaEventSources.SqsEventSource(this.multimediaProcessingQueue, {
        batchSize: 1
      })
    );

    // Grant permissions to Lambda functions
    this.grantLambdaPermissions();
  }

  private createCognitoResources() {
    // User Pool
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: 'SnapStudy-UserPool',
      selfSignUpEnabled: true,
      signInAliases: {
        email: true
      },
      autoVerify: {
        email: true
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true
        },
        fullname: {
          required: true,
          mutable: true
        }
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    // User Pool Client
    this.userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: 'SnapStudy-WebClient',
      generateSecret: false,
      authFlows: {
        userSrp: true,
        userPassword: false,
        adminUserPassword: false
      },
      preventUserExistenceErrors: true,
      refreshTokenValidity: cdk.Duration.days(30),
      accessTokenValidity: cdk.Duration.hours(1),
      idTokenValidity: cdk.Duration.hours(1)
    });
  }

  private createApiGateway() {
    // REST API Gateway
    this.restApi = new apigateway.RestApi(this, 'RestApi', {
      restApiName: 'SnapStudy-RestApi',
      description: 'REST API for SnapStudy platform',
      endpointConfiguration: {
        types: [apigateway.EndpointType.REGIONAL]
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization',
          'X-Api-Key',
          'X-Amz-Security-Token'
        ]
      },
      deployOptions: {
        stageName: 'prod'
      }
    });

    // Add Lambda integration
    const lambdaIntegration = new apigateway.LambdaIntegration(this.mainApiFunction);
    this.restApi.root.addProxy({
      defaultIntegration: lambdaIntegration
    });
  }

  private createCloudFrontDistribution() {
    // Create S3 bucket for frontend hosting
    const frontendBucket = new s3.Bucket(this, 'FrontendBucket', {
      bucketName: `snapstudy-frontend-${this.account}-${this.region}`,
      websiteIndexDocument: 'index.html',
      websiteErrorDocument: 'error.html',
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true
    });

    // Create Origin Access Identity
    const originAccessIdentity = new cloudfront.OriginAccessIdentity(this, 'OAI', {
      comment: 'SnapStudy Frontend OAI'
    });

    // Grant CloudFront access to S3 bucket
    frontendBucket.grantRead(originAccessIdentity);

    // Create CloudFront distribution
    this.distribution = new cloudfront.Distribution(this, 'Distribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(frontendBucket, {
          originAccessIdentity: originAccessIdentity
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED
      },
      additionalBehaviors: {
        '/api/*': {
          origin: new origins.RestApiOrigin(this.restApi),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER
        }
      },
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(30)
        }
      ],
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      enabled: true,
      comment: 'SnapStudy Frontend Distribution'
    });
  }

  private createCloudWatchResources() {
    // Create log groups for different services
    new logs.LogGroup(this, 'ApiGatewayLogGroup', {
      logGroupName: '/aws/apigateway/SnapStudy-RestApi',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    new logs.LogGroup(this, 'LambdaLogGroup', {
      logGroupName: '/aws/lambda/SnapStudy',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });
  }

  private createIAMRoles() {
    // Lambda execution role for authentication functions
    new iam.Role(this, 'AuthLambdaRole', {
      roleName: 'SnapStudy-AuthLambdaRole',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });
  }

  private grantLambdaPermissions() {
    // Grant DynamoDB permissions
    const tables = [
      this.usersTable,
      this.lessonsTable,
      this.microLessonsTable,
      this.quizzesTable,
      this.userEngagementTable,
      this.chatHistoryTable,
      this.audioLessonsTable,
      this.videoLessonsTable
    ];

    tables.forEach(table => {
      table.grantReadWriteData(this.mainApiFunction);
      table.grantReadWriteData(this.contentProcessorFunction);
      table.grantReadWriteData(this.multimediaProcessorFunction);
    });

    // Grant S3 permissions
    this.contentBucket.grantReadWrite(this.mainApiFunction);
    this.contentBucket.grantReadWrite(this.contentProcessorFunction);
    this.contentBucket.grantReadWrite(this.multimediaProcessorFunction);

    // Grant AWS service permissions
    const bedrockPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:InvokeModelWithResponseStream'
      ],
      resources: ['*']
    });

    const textractPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'textract:DetectDocumentText',
        'textract:AnalyzeDocument'
      ],
      resources: ['*']
    });

    const transcribePolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'transcribe:StartTranscriptionJob',
        'transcribe:GetTranscriptionJob'
      ],
      resources: ['*']
    });

    const pollyPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'polly:SynthesizeSpeech',
        'polly:DescribeVoices'
      ],
      resources: ['*']
    });

    // Add policies to functions
    this.mainApiFunction.addToRolePolicy(bedrockPolicy);
    this.contentProcessorFunction.addToRolePolicy(bedrockPolicy);
    this.contentProcessorFunction.addToRolePolicy(textractPolicy);
    this.contentProcessorFunction.addToRolePolicy(transcribePolicy);
    this.multimediaProcessorFunction.addToRolePolicy(bedrockPolicy);
    this.multimediaProcessorFunction.addToRolePolicy(pollyPolicy);
  }

  private createOutputs() {
    // API Gateway URL
    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: this.restApi.url,
      description: 'API Gateway URL'
    });

    // CloudFront Distribution URL
    new cdk.CfnOutput(this, 'CloudFrontUrl', {
      value: `https://${this.distribution.distributionDomainName}`,
      description: 'CloudFront Distribution URL'
    });

    // User Pool ID
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID'
    });

    // User Pool Client ID
    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID'
    });

    // S3 Bucket Name
    new cdk.CfnOutput(this, 'ContentBucketName', {
      value: this.contentBucket.bucketName,
      description: 'S3 Content Bucket Name'
    });
  }
}