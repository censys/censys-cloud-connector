resource "random_pet" "bucket_prefix" {
  keepers = {
    num_buckets = var.num_buckets
  }
}

resource "random_shuffle" "bucket_permissions" {
  input = [
    "private",
    "public-read",
    "public-read-write",
    "aws-exec-read",
    "authenticated-read",
    "log-delivery-write"
  ]
  result_count = var.num_buckets
}

resource "aws_s3_bucket" "buckets" {
  count         = var.num_buckets
  bucket_prefix = random_pet.bucket_prefix.id
  acl           = random_shuffle.bucket_permissions.result[count.index]
  tags = {
    Name = local.bucket_names[count.index]
  }
}
