# Terraform State Lock

## Symptoms

- `terraform plan` or `terraform apply` fails with "Error locking state"
- Message mentions DynamoDB ConditionalCheckFailedException
- Lock ID is displayed in the error

## Common Causes

1. **Previous run interrupted** — Ctrl+C during apply left a stale lock
2. **Concurrent runs** — two pipelines running Terraform on same state
3. **CI/CD timeout** — pipeline timed out during apply, lock not released
4. **DynamoDB issues** — throttling or permissions issue

## Diagnostic Commands

```bash
# Check the lock in DynamoDB (replace table name and state key)
aws dynamodb get-item --table-name terraform-locks --key '{"LockID": {"S": "<state-key>"}}'

# View who holds the lock
terraform force-unlock <LOCK_ID>  # Only if you are sure no other apply is running!
```

## Fix Steps

1. **Verify** no other Terraform process is running (check CI/CD pipelines)
2. If safe, force-unlock: `terraform force-unlock <LOCK_ID>`
3. If recurring, add timeout and retry logic to CI/CD pipeline
4. Consider using Terragrunt for better lock management
5. Review DynamoDB table IAM permissions

> ⚠️ WARNING: Only force-unlock if you are absolutely certain no other process is modifying state.
