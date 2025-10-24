import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';
export declare class SnapStudyStack extends cdk.Stack {
    usersTable: dynamodb.Table;
    lessonsTable: dynamodb.Table;
    microLessonsTable: dynamodb.Table;
    quizzesTable: dynamodb.Table;
    userEngagementTable: dynamodb.Table;
    chatHistoryTable: dynamodb.Table;
    contentBucket: s3.Bucket;
    userPool: cognito.UserPool;
    userPoolClient: cognito.UserPoolClient;
    restApi: apigateway.RestApi;
    constructor(scope: Construct, id: string, props?: cdk.StackProps);
    private createDynamoDBTables;
    private createS3Bucket;
    private createCognitoResources;
    private createApiGateway;
    private createIAMRoles;
    private createCloudWatchResources;
    private createOutputs;
}
