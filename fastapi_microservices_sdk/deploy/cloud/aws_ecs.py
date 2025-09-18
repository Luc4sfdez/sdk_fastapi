"""
AWS ECS Deployment for FastAPI Microservices.

This module provides deployment capabilities for AWS Elastic Container Service (ECS)
including Fargate and EC2 launch types with auto-scaling and load balancing.
"""

import json
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


@dataclass
class ECSTaskDefinition:
    """ECS Task Definition configuration."""
    family: str
    cpu: str = "256"
    memory: str = "512"
    network_mode: str = "awsvpc"
    requires_compatibilities: List[str] = field(default_factory=lambda: ["FARGATE"])
    execution_role_arn: Optional[str] = None
    task_role_arn: Optional[str] = None
    container_definitions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ECSService:
    """ECS Service configuration."""
    service_name: str
    cluster_name: str
    task_definition_arn: str
    desired_count: int = 2
    launch_type: str = "FARGATE"
    platform_version: str = "LATEST"
    network_configuration: Optional[Dict[str, Any]] = None
    load_balancers: List[Dict[str, Any]] = field(default_factory=list)
    service_registries: List[Dict[str, Any]] = field(default_factory=list)


class AWSECSDeployer:
    """AWS ECS deployment manager."""
    
    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for AWS ECS deployment. Install with: pip install boto3")
        
        self.region = region
        self.profile = profile
        
        # Initialize AWS clients
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.ecs_client = session.client('ecs', region_name=region)
        self.ec2_client = session.client('ec2', region_name=region)
        self.elbv2_client = session.client('elbv2', region_name=region)
        self.logs_client = session.client('logs', region_name=region)
        self.iam_client = session.client('iam', region_name=region)
    
    def create_cluster(self, cluster_name: str, capacity_providers: List[str] = None) -> Dict[str, Any]:
        """Create ECS cluster."""
        try:
            if capacity_providers is None:
                capacity_providers = ["FARGATE", "FARGATE_SPOT"]
            
            response = self.ecs_client.create_cluster(
                clusterName=cluster_name,
                capacityProviders=capacity_providers,
                defaultCapacityProviderStrategy=[
                    {
                        'capacityProvider': 'FARGATE',
                        'weight': 1,
                        'base': 1
                    },
                    {
                        'capacityProvider': 'FARGATE_SPOT',
                        'weight': 4
                    }
                ],
                tags=[
                    {
                        'key': 'CreatedBy',
                        'value': 'FastAPI-Microservices-SDK'
                    }
                ]
            )
            
            print(f"✅ Created ECS cluster: {cluster_name}")
            return response['cluster']
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ClusterAlreadyExistsException':
                print(f"ℹ️  Cluster {cluster_name} already exists")
                return self.ecs_client.describe_clusters(clusters=[cluster_name])['clusters'][0]
            else:
                raise Exception(f"Failed to create cluster: {e}")
    
    def create_task_definition(self, task_def: ECSTaskDefinition) -> str:
        """Create ECS task definition."""
        try:
            # Ensure execution role exists
            if not task_def.execution_role_arn:
                task_def.execution_role_arn = self._ensure_execution_role()
            
            response = self.ecs_client.register_task_definition(
                family=task_def.family,
                networkMode=task_def.network_mode,
                requiresCompatibilities=task_def.requires_compatibilities,
                cpu=task_def.cpu,
                memory=task_def.memory,
                executionRoleArn=task_def.execution_role_arn,
                taskRoleArn=task_def.task_role_arn,
                containerDefinitions=task_def.container_definitions
            )
            
            task_def_arn = response['taskDefinition']['taskDefinitionArn']
            print(f"✅ Created task definition: {task_def_arn}")
            return task_def_arn
            
        except ClientError as e:
            raise Exception(f"Failed to create task definition: {e}")
    
    def create_service(self, service_config: ECSService) -> Dict[str, Any]:
        """Create ECS service."""
        try:
            service_params = {
                'serviceName': service_config.service_name,
                'cluster': service_config.cluster_name,
                'taskDefinition': service_config.task_definition_arn,
                'desiredCount': service_config.desired_count,
                'launchType': service_config.launch_type,
                'platformVersion': service_config.platform_version,
                'tags': [
                    {
                        'key': 'CreatedBy',
                        'value': 'FastAPI-Microservices-SDK'
                    }
                ]
            }
            
            if service_config.network_configuration:
                service_params['networkConfiguration'] = service_config.network_configuration
            
            if service_config.load_balancers:
                service_params['loadBalancers'] = service_config.load_balancers
            
            if service_config.service_registries:
                service_params['serviceRegistries'] = service_config.service_registries
            
            response = self.ecs_client.create_service(**service_params)
            
            print(f"✅ Created ECS service: {service_config.service_name}")
            return response['service']
            
        except ClientError as e:
            raise Exception(f"Failed to create service: {e}")
    
    def deploy_fastapi_app(self, app_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy FastAPI application to ECS."""
        app_name = app_config.get('app_name', 'fastapi-app')
        image_uri = app_config.get('image_uri')
        port = app_config.get('port', 8000)
        cpu = app_config.get('cpu', '256')
        memory = app_config.get('memory', '512')
        desired_count = app_config.get('desired_count', 2)
        
        if not image_uri:
            raise ValueError("image_uri is required for deployment")
        
        # Create cluster
        cluster_name = f"{app_name}-cluster"
        cluster = self.create_cluster(cluster_name)
        
        # Create log group
        log_group_name = f"/ecs/{app_name}"
        self._create_log_group(log_group_name)
        
        # Create task definition
        container_def = {
            "name": app_name,
            "image": image_uri,
            "portMappings": [
                {
                    "containerPort": port,
                    "protocol": "tcp"
                }
            ],
            "essential": True,
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": log_group_name,
                    "awslogs-region": self.region,
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "environment": [
                {
                    "name": "PORT",
                    "value": str(port)
                },
                {
                    "name": "ENVIRONMENT",
                    "value": "production"
                }
            ],
            "healthCheck": {
                "command": [
                    "CMD-SHELL",
                    f"curl -f http://localhost:{port}/health || exit 1"
                ],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
        
        task_def = ECSTaskDefinition(
            family=f"{app_name}-task",
            cpu=cpu,
            memory=memory,
            container_definitions=[container_def]
        )
        
        task_def_arn = self.create_task_definition(task_def)
        
        # Get default VPC and subnets
        vpc_id, subnet_ids = self._get_default_vpc_subnets()
        
        # Create security group
        security_group_id = self._create_security_group(app_name, vpc_id, port)
        
        # Create service
        service_config = ECSService(
            service_name=f"{app_name}-service",
            cluster_name=cluster_name,
            task_definition_arn=task_def_arn,
            desired_count=desired_count,
            network_configuration={
                'awsvpcConfiguration': {
                    'subnets': subnet_ids,
                    'securityGroups': [security_group_id],
                    'assignPublicIp': 'ENABLED'
                }
            }
        )
        
        service = self.create_service(service_config)
        
        # Wait for service to be stable
        print("⏳ Waiting for service to become stable...")
        self._wait_for_service_stable(cluster_name, service_config.service_name)
        
        # Get service endpoint
        endpoint = self._get_service_endpoint(cluster_name, service_config.service_name)
        
        return {
            'cluster_name': cluster_name,
            'service_name': service_config.service_name,
            'task_definition_arn': task_def_arn,
            'endpoint': endpoint,
            'status': 'deployed'
        }
    
    def update_service(self, cluster_name: str, service_name: str, 
                      task_definition_arn: str) -> Dict[str, Any]:
        """Update ECS service with new task definition."""
        try:
            response = self.ecs_client.update_service(
                cluster=cluster_name,
                service=service_name,
                taskDefinition=task_definition_arn
            )
            
            print(f"✅ Updated service: {service_name}")
            
            # Wait for deployment to complete
            print("⏳ Waiting for deployment to complete...")
            self._wait_for_service_stable(cluster_name, service_name)
            
            return response['service']
            
        except ClientError as e:
            raise Exception(f"Failed to update service: {e}")
    
    def delete_service(self, cluster_name: str, service_name: str) -> bool:
        """Delete ECS service."""
        try:
            # Scale down to 0
            self.ecs_client.update_service(
                cluster=cluster_name,
                service=service_name,
                desiredCount=0
            )
            
            # Wait for tasks to stop
            self._wait_for_service_stable(cluster_name, service_name)
            
            # Delete service
            self.ecs_client.delete_service(
                cluster=cluster_name,
                service=service_name
            )
            
            print(f"✅ Deleted service: {service_name}")
            return True
            
        except ClientError as e:
            print(f"❌ Failed to delete service: {e}")
            return False
    
    def get_service_logs(self, cluster_name: str, service_name: str, 
                        lines: int = 100) -> List[str]:
        """Get service logs from CloudWatch."""
        try:
            log_group_name = f"/ecs/{service_name.replace('-service', '')}"
            
            response = self.logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if not response['logStreams']:
                return []
            
            log_stream_name = response['logStreams'][0]['logStreamName']
            
            response = self.logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                limit=lines,
                startFromHead=False
            )
            
            return [event['message'] for event in response['events']]
            
        except ClientError as e:
            print(f"❌ Failed to get logs: {e}")
            return []
    
    def _ensure_execution_role(self) -> str:
        """Ensure ECS execution role exists."""
        role_name = "ecsTaskExecutionRole"
        
        try:
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                # Create the role
                trust_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "ecs-tasks.amazonaws.com"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }
                
                response = self.iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description="ECS Task Execution Role"
                )
                
                # Attach policy
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
                )
                
                return response['Role']['Arn']
            else:
                raise
    
    def _create_log_group(self, log_group_name: str) -> None:
        """Create CloudWatch log group."""
        try:
            self.logs_client.create_log_group(
                logGroupName=log_group_name,
                tags={
                    'CreatedBy': 'FastAPI-Microservices-SDK'
                }
            )
            print(f"✅ Created log group: {log_group_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print(f"ℹ️  Log group {log_group_name} already exists")
            else:
                raise
    
    def _get_default_vpc_subnets(self) -> tuple:
        """Get default VPC and subnets."""
        # Get default VPC
        vpcs = self.ec2_client.describe_vpcs(
            Filters=[{'Name': 'isDefault', 'Values': ['true']}]
        )
        
        if not vpcs['Vpcs']:
            raise Exception("No default VPC found")
        
        vpc_id = vpcs['Vpcs'][0]['VpcId']
        
        # Get public subnets
        subnets = self.ec2_client.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'default-for-az', 'Values': ['true']}
            ]
        )
        
        subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
        
        return vpc_id, subnet_ids
    
    def _create_security_group(self, app_name: str, vpc_id: str, port: int) -> str:
        """Create security group for the application."""
        sg_name = f"{app_name}-sg"
        
        try:
            response = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description=f"Security group for {app_name}",
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        'ResourceType': 'security-group',
                        'Tags': [
                            {
                                'Key': 'Name',
                                'Value': sg_name
                            },
                            {
                                'Key': 'CreatedBy',
                                'Value': 'FastAPI-Microservices-SDK'
                            }
                        ]
                    }
                ]
            )
            
            security_group_id = response['GroupId']
            
            # Add ingress rules
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': port,
                        'ToPort': port,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            
            print(f"✅ Created security group: {sg_name}")
            return security_group_id
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
                # Get existing security group
                response = self.ec2_client.describe_security_groups(
                    Filters=[
                        {'Name': 'group-name', 'Values': [sg_name]},
                        {'Name': 'vpc-id', 'Values': [vpc_id]}
                    ]
                )
                return response['SecurityGroups'][0]['GroupId']
            else:
                raise
    
    def _wait_for_service_stable(self, cluster_name: str, service_name: str, 
                                timeout: int = 600) -> None:
        """Wait for service to become stable."""
        waiter = self.ecs_client.get_waiter('services_stable')
        waiter.wait(
            cluster=cluster_name,
            services=[service_name],
            WaiterConfig={
                'Delay': 15,
                'MaxAttempts': timeout // 15
            }
        )
        print(f"✅ Service {service_name} is now stable")
    
    def _get_service_endpoint(self, cluster_name: str, service_name: str) -> Optional[str]:
        """Get service public endpoint."""
        try:
            # Get service tasks
            response = self.ecs_client.list_tasks(
                cluster=cluster_name,
                serviceName=service_name
            )
            
            if not response['taskArns']:
                return None
            
            # Get task details
            task_response = self.ecs_client.describe_tasks(
                cluster=cluster_name,
                tasks=response['taskArns']
            )
            
            for task in task_response['tasks']:
                for attachment in task.get('attachments', []):
                    if attachment['type'] == 'ElasticNetworkInterface':
                        for detail in attachment['details']:
                            if detail['name'] == 'networkInterfaceId':
                                eni_id = detail['value']
                                
                                # Get ENI public IP
                                eni_response = self.ec2_client.describe_network_interfaces(
                                    NetworkInterfaceIds=[eni_id]
                                )
                                
                                if eni_response['NetworkInterfaces']:
                                    public_ip = eni_response['NetworkInterfaces'][0].get('Association', {}).get('PublicIp')
                                    if public_ip:
                                        return f"http://{public_ip}:8000"
            
            return None
            
        except ClientError:
            return None


def deploy_to_aws_ecs(config: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy FastAPI application to AWS ECS."""
    region = config.get('region', 'us-east-1')
    profile = config.get('profile')
    
    deployer = AWSECSDeployer(region=region, profile=profile)
    return deployer.deploy_fastapi_app(config)


def generate_ecs_deployment_config(app_name: str, image_uri: str) -> Dict[str, Any]:
    """Generate ECS deployment configuration."""
    return {
        'app_name': app_name,
        'image_uri': image_uri,
        'port': 8000,
        'cpu': '256',
        'memory': '512',
        'desired_count': 2,
        'region': 'us-east-1'
    }