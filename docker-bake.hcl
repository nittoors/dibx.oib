group "default" {
  targets = ["oib-api", "oib-web", "oib-jobs"]
}

variable "SOURCE_REVISION" {
  default = "uncommitted-local"
}

target "common" {
  platforms = ["linux/arm64"]
  args = {
    SOURCE_REPOSITORY = "https://github.com/Nittoors/dibx.oib"
    SOURCE_REVISION   = SOURCE_REVISION
  }
}

target "oib-api" {
  inherits   = ["common"]
  context    = "apps/oib-api"
  dockerfile = "Dockerfile.production"
  tags       = ["dibx/oib-api:validation"]
}

target "oib-web" {
  inherits   = ["common"]
  context    = "."
  dockerfile = "apps/oib-web/Dockerfile.production"
  tags       = ["dibx/oib-web:validation"]
}

target "oib-jobs" {
  inherits   = ["common"]
  context    = "."
  dockerfile = "apps/oib-api/Dockerfile.jobs"
  tags       = ["dibx/oib-jobs:validation"]
}
