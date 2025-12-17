# src/pkgmgr/core/git/commands/__init__.py
from __future__ import annotations

from .add import GitAddError, add
from .add_all import GitAddAllError, add_all
from .add_remote import GitAddRemoteError, add_remote
from .add_remote_push_url import GitAddRemotePushUrlError, add_remote_push_url
from .branch_move import GitBranchMoveError, branch_move
from .checkout import GitCheckoutError, checkout
from .clone import GitCloneError, clone
from .commit import GitCommitError, commit
from .create_branch import GitCreateBranchError, create_branch
from .delete_local_branch import GitDeleteLocalBranchError, delete_local_branch
from .delete_remote_branch import GitDeleteRemoteBranchError, delete_remote_branch
from .fetch import GitFetchError, fetch
from .init import GitInitError, init
from .merge_no_ff import GitMergeError, merge_no_ff
from .pull import GitPullError, pull
from .pull_args import GitPullArgsError, pull_args
from .pull_ff_only import GitPullFfOnlyError, pull_ff_only
from .push import GitPushError, push
from .push_upstream import GitPushUpstreamError, push_upstream
from .set_remote_url import GitSetRemoteUrlError, set_remote_url
from .tag_annotated import GitTagAnnotatedError, tag_annotated
from .tag_force_annotated import GitTagForceAnnotatedError, tag_force_annotated

__all__ = [
    "add",
    "add_all",
    "fetch",
    "checkout",
    "pull",
    "pull_args",
    "pull_ff_only",
    "merge_no_ff",
    "push",
    "commit",
    "delete_local_branch",
    "delete_remote_branch",
    "create_branch",
    "push_upstream",
    "add_remote",
    "set_remote_url",
    "add_remote_push_url",
    "tag_annotated",
    "tag_force_annotated",
    "clone",
    "init",
    "branch_move",
    "GitAddError",
    "GitAddAllError",
    "GitFetchError",
    "GitCheckoutError",
    "GitPullError",
    "GitPullArgsError",
    "GitPullFfOnlyError",
    "GitMergeError",
    "GitPushError",
    "GitCommitError",
    "GitDeleteLocalBranchError",
    "GitDeleteRemoteBranchError",
    "GitCreateBranchError",
    "GitPushUpstreamError",
    "GitAddRemoteError",
    "GitSetRemoteUrlError",
    "GitAddRemotePushUrlError",
    "GitTagAnnotatedError",
    "GitTagForceAnnotatedError",
    "GitCloneError",
    "GitInitError",
    "GitBranchMoveError",
]
