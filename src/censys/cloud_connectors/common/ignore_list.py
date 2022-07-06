"""Ignored IPs and domains."""
IGNORED_IPS = {
    # AWS Ignored
    "0.0.0.0",
    # Cloudflare
    "1.0.0.1",
    "1.1.1.1",
    "1.1.1.2",
    "4.4.4.4",
    # Google
    "8.8.4.4",
    "8.8.8.8",
    # Quad9
    "9.9.9.9",
    "9.9.9.10",
    "149.112.112.112",
    # OpenDNS
    "208.67.220.220",
    "208.67.222.222",
    # Level3
    "209.244.0.3",
    "209.244.0.4",
    # Verisign
    "64.6.64.6",
    "64.6.65.6",
    # DNS.WATCH
    "84.200.69.80",
    "84.200.70.40",
    # Comodo
    "8.26.56.26",
    "8.20.247.20",
    # OpenDNS
    "208.67.222.222",
    "208.67.220.220",
    # Norton ConnectSafe
    "199.85.126.10",
    "199.85.127.10",
}

IGNORED_DOMAINS = {
    "amazonaws.com",
    "amazonaws.com",
    "autodiscover.outlook.com",
    "aws.com",
    "azure.com",
    "google.com",
    "lync.com",
    "microsoft.com",
    "sendgrid.net",
    "webdir.online.lync.com",
    "windows.net",
    "www.google.com",
    "www.microsoft.com",
}
