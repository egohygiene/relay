#!/usr/bin/env bash
# shellcheck shell=bash
# Copyright 2026 Ego Hygiene
# SPDX-License-Identifier: MIT

set -euo pipefail

# @description Print an error and return a stable validation status.
# @arg $@ string Error message.
fail_validation() {
  printf '%s\n' "$*" >&2
  return 2
}

# @description Reject untrusted events, tags, and non-default branches.
validate_trust_boundary() {
  case "${GITHUB_EVENT_NAME:-}" in
    push | schedule | workflow_dispatch) ;;
    *)
      fail_validation \
        "Report publication is forbidden for event: ${GITHUB_EVENT_NAME:-unknown}"
      return
      ;;
  esac

  if [[ -n "${GITHUB_REF_TYPE:-}" && "${GITHUB_REF_TYPE}" != "branch" ]]; then
    fail_validation "Report publication requires a branch ref; received ${GITHUB_REF_TYPE}."
    return
  fi
  if [[ "${GITHUB_REF_NAME:-}" != "${INPUT_DEFAULT_BRANCH}" ]]; then
    fail_validation \
      "Report publication requires default branch ${INPUT_DEFAULT_BRANCH}; received ${GITHUB_REF_NAME:-unknown}."
    return
  fi
}

# @description Return success for one canonical report-only path.
# @arg $1 string Repository-relative report path.
validate_report_path() {
  local report_path="$1"
  if [[ ! "${report_path}" =~ ^\.reports/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+/?$ ]]; then
    fail_validation "Report path must be a literal traversal-free path under .reports/: ${report_path}"
    return
  fi
  case "/${report_path}/" in
    */../* | */./* | */history/*)
      fail_validation "Report path must not contain dot or history components: ${report_path}"
      return
      ;;
    *) ;;
  esac
  if [[ ! -e "${report_path}" ]]; then
    fail_validation "Report snapshot does not exist: ${report_path}"
    return
  fi
  local component=""
  local path_part
  local -a path_parts
  IFS='/' read -r -a path_parts <<< "${report_path}"
  for path_part in "${path_parts[@]}"; do
    component="${component:+${component}/}${path_part}"
    if [[ -L "${component}" ]]; then
      fail_validation "Report paths must not contain symbolic links: ${report_path}"
      return
    fi
  done
  if find "${report_path}" -type l -print -quit | grep --quiet .; then
    fail_validation "Report snapshots must not contain symbolic links: ${report_path}"
    return
  fi
  if find "${report_path}" -type d -name history -print -quit | grep --quiet .; then
    fail_validation "Timestamped history directories are forbidden: ${report_path}"
    return
  fi
}

# @description Parse report-only inputs into REPORT_PATHS.
# @set REPORT_PATHS Validated report paths in caller scope.
parse_report_paths() {
  local report_path
  REPORT_PATHS=()
  while IFS= read -r report_path; do
    [[ -n "${report_path}" ]] || continue
    validate_report_path "${report_path}"
    REPORT_PATHS+=("${report_path}")
  done <<< "${INPUT_PATHS}"

  if ((${#REPORT_PATHS[@]} == 0)); then
    fail_validation "paths must contain at least one report path."
  fi
}

# @description Confirm staging contains only stable .reports paths.
validate_staged_paths() {
  local staged_path
  while IFS= read -r staged_path; do
    [[ -n "${staged_path}" ]] || continue
    case "/${staged_path}/" in
      /.reports/*)
        if [[ "/${staged_path}/" == */history/* ]]; then
          fail_validation "Staged history paths are forbidden: ${staged_path}"
          return
        fi
        ;;
      *)
        fail_validation "Refusing staged path outside .reports/: ${staged_path}"
        return
        ;;
    esac
  done < <(git diff --cached --name-only --diff-filter=ACDMRTUXB)
}

# @description Write action outputs when a GitHub output file is available.
# @arg $1 string Whether publication changed the repository.
# @arg $2 string Created commit SHA or empty string.
write_outputs() {
  local changed="$1"
  local commit_sha="$2"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf 'changed=%s\n' "${changed}" >> "${GITHUB_OUTPUT}"
    printf 'commit-sha=%s\n' "${commit_sha}" >> "${GITHUB_OUTPUT}"
  fi
}

# @description Push the current commit with bounded race retries.
push_with_retry() {
  local attempt
  for attempt in 1 2 3; do
    git pull --rebase origin "${INPUT_DEFAULT_BRANCH}"
    if git push origin "HEAD:${INPUT_DEFAULT_BRANCH}"; then
      return 0
    fi
    if ((attempt == 3)); then
      printf 'Unable to publish after %s attempts.\n' "${attempt}" >&2
      return 1
    fi
    printf 'Report push raced with another writer; retrying (%s/3).\n' \
      "${attempt}" >&2
    sleep "$((attempt * 2))"
  done
}

# @description Guard, stage, commit, and publish the requested report snapshots.
main() {
  : "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"
  : "${INPUT_AUTHOR_EMAIL:?author-email is required}"
  : "${INPUT_AUTHOR_NAME:?author-name is required}"
  : "${INPUT_COMMIT_MESSAGE:?commit-message is required}"
  : "${INPUT_DEFAULT_BRANCH:?default-branch is required}"
  : "${INPUT_PATHS:?paths is required}"

  cd "${GITHUB_WORKSPACE}"
  validate_trust_boundary
  parse_report_paths

  git rev-parse --is-inside-work-tree >/dev/null
  git config user.name "${INPUT_AUTHOR_NAME}"
  git config user.email "${INPUT_AUTHOR_EMAIL}"
  git --literal-pathspecs add --force --all -- "${REPORT_PATHS[@]}"
  validate_staged_paths

  if git diff --cached --quiet; then
    printf 'No curated report changes to publish.\n'
    write_outputs "false" ""
    return 0
  fi

  git commit --message "${INPUT_COMMIT_MESSAGE}"
  push_with_retry
  local commit_sha
  commit_sha="$(git rev-parse HEAD)"
  write_outputs "true" "${commit_sha}"
}

main "$@"
