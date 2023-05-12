resource "random_pet" "db_prefix" {
  keepers = {
    num_db_instances = var.num_db_instances
  }
}

resource "random_pet" "db_username" {
  keepers = {
    num_db_instances = var.num_db_instances
  }
}

resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "random_shuffle" "db_engine" {
  input = [
    "mysql",
    "postgres"
  ]
  result_count = var.num_db_instances
}

resource "random_shuffle" "db_public" {
  input = [
    true,
    false
  ]
  result_count = var.num_db_instances
}

resource "aws_db_instance" "db_instances" {
  count               = var.num_db_instances
  identifier          = "${random_pet.db_prefix.id}-${count.index}"
  allocated_storage   = 5
  engine              = random_shuffle.db_engine.result[count.index]
  instance_class      = "db.t2.micro" # Smallest available
  name                = "${random_pet.db_prefix.id}-${count.index}"
  username            = random_pet.db_username.id
  password            = random_password.db_password.result
  skip_final_snapshot = true
  publicly_accessible = random_shuffle.db_public.result[count.index]
  tags = {
    Name = "${random_pet.db_prefix.id}-${count.index}"
  }
}
