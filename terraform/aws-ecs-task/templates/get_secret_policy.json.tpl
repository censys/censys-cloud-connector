{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": [
                "${providers_arn}",
                "${censys_api_key_arn}"
            ]
        }
    ]
}
