#!/usr/bin/env bash
set -euo pipefail

log()  { echo "[cleanup] $*"; }
warn() { echo "[cleanup][WARN] $*" >&2; }

MODE="${MODE:-safe}" # safe | aggressive
# safe: caches/logs/tmp only
# aggressive: safe + docs/man/info (optional)

ID="unknown"
if [ -f /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  ID="${ID:-unknown}"
fi

log "Starting image cleanup"
log "Mode: ${MODE}"
log "Detected OS: ${ID}"

# ------------------------------------------------------------
# Package manager caches (SAFE)
# ------------------------------------------------------------
case "${ID}" in
  alpine)
    log "Cleaning apk cache"
    if [ -d /var/cache/apk ]; then
      du -sh /var/cache/apk || true
      rm -rvf /var/cache/apk/* || true
    else
      log "apk cache directory not present (already clean)"
    fi
    ;;
  arch)
    log "Cleaning pacman cache"
    du -sh /var/cache/pacman/pkg 2>/dev/null || true
    pacman -Scc --noconfirm || true
    rm -rvf /var/cache/pacman/pkg/* || true
    ;;
  debian|ubuntu)
    log "Cleaning apt cache"
    du -sh /var/lib/apt/lists 2>/dev/null || true
    apt-get clean || true
    rm -rvf /var/lib/apt/lists/* || true
    ;;
  fedora)
    log "Cleaning dnf cache"
    du -sh /var/cache/dnf 2>/dev/null || true
    dnf clean all || true
    rm -rvf /var/cache/dnf/* || true
    ;;
  centos|rhel)
    log "Cleaning yum/dnf cache"
    du -sh /var/cache/yum /var/cache/dnf 2>/dev/null || true
    (command -v dnf >/dev/null 2>&1 && dnf clean all) || true
    (command -v yum >/dev/null 2>&1 && yum clean all) || true
    rm -rvf /var/cache/yum/* /var/cache/dnf/* || true
    ;;
  *)
    warn "Unknown distro '${ID}' — skipping package manager cleanup"
    ;;
esac

# ------------------------------------------------------------
# Python caches (SAFE)
# ------------------------------------------------------------
log "Cleaning pip cache"
du -sh /root/.cache/pip 2>/dev/null || true
rm -rvf /root/.cache/pip 2>/dev/null || true
rm -rvf /home/*/.cache/pip 2>/dev/null || true

log "Cleaning __pycache__ directories"
find /opt /usr /root /home -type d -name "__pycache__" -print -prune 2>/dev/null || true
find /opt /usr /root /home -type d -name "__pycache__" -prune -exec rm -rvf {} + 2>/dev/null || true

# ------------------------------------------------------------
# Logs (SAFE)
# ------------------------------------------------------------
log "Truncating log files (keeping paths intact)"
if [ -d /var/log ]; then
  find /var/log -type f -name "*.log" -print 2>/dev/null || true
  find /var/log -type f -name "*.log" -exec sh -lc ': > "$1" 2>/dev/null || true' _ {} \; 2>/dev/null || true
  
  find /var/log -type f -name "*.out" -print 2>/dev/null || true
  find /var/log -type f -name "*.out" -exec sh -lc ': > "$1" 2>/dev/null || true' _ {} \; 2>/dev/null || true
fi

if command -v journalctl >/dev/null 2>&1; then
  log "Vacuuming journald logs"
  journalctl --disk-usage || true
  journalctl --vacuum-size=10M || true
  journalctl --vacuum-time=1s || true
  journalctl --disk-usage || true
else
  log "journald not present (skipping)"
fi

# ------------------------------------------------------------
# Temporary files (SAFE)
# ------------------------------------------------------------
log "Cleaning temporary directories"
if [ -d /tmp ]; then
  du -sh /tmp 2>/dev/null || true
  rm -rvf /tmp/* || true
fi

if [ -d /var/tmp ]; then
  du -sh /var/tmp 2>/dev/null || true
  rm -rvf /var/tmp/* || true
fi

# ------------------------------------------------------------
# Generic caches (SAFE)
# ------------------------------------------------------------
log "Cleaning generic caches"
du -sh /root/.cache 2>/dev/null || true
rm -rvf /root/.cache/* 2>/dev/null || true
rm -rvf /home/*/.cache/* 2>/dev/null || true

# ------------------------------------------------------------
# Optional aggressive extras (still safe for runtime)
# ------------------------------------------------------------
if [[ "${MODE}" == "aggressive" ]]; then
  log "Aggressive mode enabled: removing docs/man/info"
  du -sh /usr/share/doc /usr/share/man /usr/share/info 2>/dev/null || true
  rm -rvf /usr/share/doc/* /usr/share/man/* /usr/share/info/* 2>/dev/null || true
fi

log "Cleanup finished successfully"
