resource "aws_route53_record" "domain" {
  zone_id                  = data.aws_route53_zone.primary.zone_id
  name                     = var.dns ["name"]
  type                     = "A"
  alias {
    name                   = aws_alb.load_balancer.dns_name
    zone_id                = aws_alb.load_balancer.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "alter_domains" {
  count = length (var.dns ["alt_names"])
  zone_id                  = data.aws_route53_zone.primary.zone_id
  name                     = var.dns ["alt_names"][count.index]
  type                     = "A"
  alias {
    name                   = aws_alb.load_balancer.dns_name
    zone_id                = aws_alb.load_balancer.zone_id
    evaluate_target_health = true
  }
}

resource "aws_acm_certificate" "cert" {
  domain_name               = var.dns ["name"]
  subject_alternative_names = var.dns ["alt_names"]
  validation_method         = "DNS"
  lifecycle {
    create_before_destroy   = true
  }
}

resource "aws_route53_record" "example" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.primary.zone_id
}

resource "aws_acm_certificate_validation" "example" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.example : record.fqdn]
}
