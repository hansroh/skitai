

resource "aws_s3_bucket" "b" {
  bucket = "${var.cluster_name}.public"
  tags = {
    Name        = "${var.cluster_name}.public"
  }
}

resource "aws_s3_bucket_ownership_controls" "example" {
  bucket = aws_s3_bucket.b.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.b.id

  block_public_acls   = false
  ignore_public_acls  = false
  block_public_policy = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "s3_config" {
  bucket = aws_s3_bucket.b.id

  cors_rule {
      allowed_headers = ["*"]
      allowed_methods = ["PUT", "GET", "POST", "DELETE", "HEAD"]
      allowed_origins = concat (
        [
          "http://localhost:8081",
          "https://${var.dns.name}"
        ],
        [ for name in var.dns.alt_names : "https://${name}" ]
      )
      expose_headers = ["ETag"]
      max_age_seconds = 3000
  }
}

resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${var.cluster_name} identity pool"
  allow_unauthenticated_identities = false
  allow_classic_flow               = false
}



# authentificated ----------------------------------------
resource "aws_iam_role" "authenticated" {
  name = "${var.cluster_name}_cognito_authenticated"
  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Federated": "cognito-identity.amazonaws.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
          "StringEquals": {
            "cognito-identity.amazonaws.com:aud": "${aws_cognito_identity_pool.main.id}"
          },
          "ForAnyValue:StringLike": {
            "cognito-identity.amazonaws.com:amr": "authenticated"
          }
        }
      }
    ]
}
EOF
}

resource "aws_iam_role_policy" "authenticated" {
  name = "${var.cluster_name}_cognito_authenticated_policy"
  role = aws_iam_role.authenticated.id
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "mobileanalytics:PutEvents",
                "cognito-sync:*",
                "cognito-identity:*"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
EOF
}



# unauthentificated ----------------------------------------
resource "aws_iam_role" "unauthenticated" {
  name = "${var.cluster_name}_cognito_unauthenticated"
  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "cognito-identity.amazonaws.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "cognito-identity.amazonaws.com:aud": "${aws_cognito_identity_pool.main.id}"
                },
                "ForAnyValue:StringLike": {
                    "cognito-identity.amazonaws.com:amr": "unauthenticated"
                }
            }
        }
    ]
}
EOF
}

resource "aws_iam_role_policy" "unauthenticated" {
  name = "${var.cluster_name}_cognito_unauthenticated_policy"
  role = aws_iam_role.unauthenticated.id
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::${aws_s3_bucket.b.bucket}/*",
                "arn:aws:s3:::${aws_s3_bucket.b.bucket}"
            ]
        }
    ]
}
EOF
}



# attach roles -------------------------------------
resource "aws_cognito_identity_pool_roles_attachment" "main" {
      identity_pool_id = aws_cognito_identity_pool.main.id
      roles = {
           "authenticated"   = aws_iam_role.authenticated.arn
           "unauthenticated" = aws_iam_role.unauthenticated.arn
     }
 }
