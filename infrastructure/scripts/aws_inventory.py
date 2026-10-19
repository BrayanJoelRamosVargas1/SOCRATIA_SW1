"""Read-only AWS inventory. Run in AWS CloudShell or with an authenticated AWS CLI."""
import argparse
import json
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--region", required=True)
args = parser.parse_args()
commands = {
    "identity": ["sts", "get-caller-identity"],
    "stacks": ["cloudformation", "describe-stacks", "--query", "Stacks[].{Name:StackName,Status:StackStatus,Id:StackId,Tags:Tags}"],
    "instances": ["ec2", "describe-instances", "--query", "Reservations[].Instances[].{Id:InstanceId,State:State.Name,Type:InstanceType,IP:PublicIpAddress,Tags:Tags}"],
    "volumes": ["ec2", "describe-volumes", "--query", "Volumes[].{Id:VolumeId,Size:Size,State:State,Tags:Tags}"],
    "addresses": ["ec2", "describe-addresses", "--query", "Addresses[].{Id:AllocationId,IP:PublicIp,Instance:InstanceId,Tags:Tags}"],
    "nat_gateways": ["ec2", "describe-nat-gateways", "--query", "NatGateways[].{Id:NatGatewayId,State:State,Tags:Tags}"],
    "databases": ["rds", "describe-db-instances", "--query", "DBInstances[].{Id:DBInstanceIdentifier,Status:DBInstanceStatus,Class:DBInstanceClass,Storage:AllocatedStorage,Arn:DBInstanceArn}"],
    "load_balancers": ["elbv2", "describe-load-balancers", "--query", "LoadBalancers[].{Name:LoadBalancerName,Arn:LoadBalancerArn,State:State.Code}"],
    "ecs_clusters": ["ecs", "list-clusters"],
    "lightsail": ["lightsail", "get-instances", "--query", "instances[].{Name:name,State:state.name,Bundle:bundleId,IP:publicIpAddress,Tags:tags}"],
    "ecr": ["ecr", "describe-repositories", "--query", "repositories[].{Name:repositoryName,Arn:repositoryArn}"],
    "buckets": ["s3api", "list-buckets", "--query", "Buckets[].Name"],
}
result = {"region": args.region, "read_only": True, "resources": {}}
for name, command in commands.items():
    completed = subprocess.run(["aws", *command, "--region", args.region, "--output", "json", "--no-cli-pager"], capture_output=True, text=True)
    if completed.returncode:
        result["resources"][name] = {"unavailable": True, "reason": completed.stderr.strip()[:500]}
    else:
        result["resources"][name] = json.loads(completed.stdout)
print(json.dumps(result, indent=2))
