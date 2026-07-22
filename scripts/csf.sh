#!/bin/bash

# Tunnel CSF via SSH
connect_csf() {
  if [[ -z "${CSF_USERNAME:-}" || -z "${CSF_HOST:-}" ]]; then
    local repo_root="${FIL_SRL_ROOT:-/workspaces/fil-srl}"
    local env_file="${repo_root}/.env"

    if [[ -f "$env_file" ]]; then
      set -a
      # shellcheck disable=SC1090
      . "$env_file"
      set +a
    fi
  fi

  local node_number="${1:-}"
  local csf_username="${CSF_USERNAME:-}"
  local csf_host="${CSF_HOST:-}"
  local ssh_args=()

  if [[ -z "$node_number" ]]; then
    read -rp "Node number (optional, e.g., 872): " node_number
  fi

  if [[ -z "$csf_username" ]]; then
    read -rp "CSF username: " csf_username
  fi

  if [[ -z "$csf_host" ]]; then
    read -rp "CSF host: " csf_host
  fi

  [[ -n "$node_number" ]] && ssh_args+=( -L "11434:node${node_number}:11434" )
  ssh "${ssh_args[@]}" "${csf_username}@${csf_host}"
}