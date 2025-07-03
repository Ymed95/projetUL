variable "resource_group_name" {
  type    = string
  default = "filrouge-rg"
}

variable "location" {
  type    = string
  default = "westeurope"
}

variable "vm_admin_username" {
  type    = string
  default = "azureuser"
}

variable "vm_size" {
  type    = string
  default = "Standard_B1s"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_rsa.pub"
}

