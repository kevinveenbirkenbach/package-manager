# flake.nix
# This file defines a Nix flake providing a reproducible development environment
# and optional installation package for the package-manager tool.

{
  description = "Nix flake for Kevin's package-manager tool";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in {

      # Development environment used via: nix develop
      devShells.default = pkgs.mkShell {
        # System packages for development
        buildInputs = [
          pkgs.python311
          pkgs.python311Packages.pyyaml
          pkgs.git
        ];

        # Message shown on environment entry
        shellHook = ''
          echo "Entered pkgmgr development environment";
        '';
      };

      # Optional installable package for "nix profile install"
      packages.pkgmgr = pkgs.python311Packages.buildPythonApplication {
        pname = "package-manager";
        version = "0.1.0";
        src = ./.;
        propagatedBuildInputs = [ pkgs.python311Packages.pyyaml ];
      };
    };
}
