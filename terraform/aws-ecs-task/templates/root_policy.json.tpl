{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "${account_id}"
            },
            "Action": [
                "sts:AssumeRole"
            ]
        }
    ]
}
