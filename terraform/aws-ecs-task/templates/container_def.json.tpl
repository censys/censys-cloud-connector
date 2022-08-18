[
    {
        "name": "cloud_connector",
        "image": "${image}",
        "essential": true,
        "entryPoint": ["/app/.venv/bin/python3"],
        "command": ["/app/src/censys/cloud_connectors/aws_connector/serverless.py"],
        "environment": [
            {
            "name": "LOGGING_LEVEL",
            "value": "${logging_level}"
            }
        ],
        "secrets": [
            {
                "name": "CENSYS_API_KEY",
                "valueFrom": "${censys_asm_api_key_secret_arn}"
            },
            {
                "name": "PROVIDERS_SECRETS",
                "valueFrom": "${providers_secret_arn}"
            }
        ],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
            "awslogs-group": "${awslogs_group}",
            "awslogs-region": "${awslogs_region}",
            "awslogs-stream-prefix": "cloud_connector"
            }
        }
    }
]
