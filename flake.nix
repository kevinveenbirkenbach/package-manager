{
  description = "Nix flake for Kevin's package-manager tool";

  nixConfig = {
    extra-experimental-features = [ "nix-command" "flakes" ];
  };

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];

      forAllSystems = f:
        builtins.listToAttrs (map (system: {
          name = system;
          value = f system;
        }) systems);
    in
    {
      ##########################################################################
      # PACKAGES
      ##########################################################################
      packages = forAllSystems (system:
        let
          pkgs   = nixpkgs.legacyPackages.${system};
          pyPkgs = pkgs.python311Packages;
        in
        rec {
          pkgmgr = pyPkgs.buildPythonApplication {
            pname   = "package-manager";
            version = "0.9.1";

            # Use the git repo as source
            src = ./.;

            # Build using pyproject.toml
            format = "pyproject";

            # Build backend requirements from [build-system]
            nativeBuildInputs = [
              pyPkgs.setuptools
              pyPkgs.wheel
            ];

            # Runtime dependencies (matches [project.dependencies] in pyproject.toml)
            propagatedBuildInputs = [
              pyPkgs.pyyaml
              pyPkgs.pip
            ];

            doCheck = false;

            pythonImportsCheck = [ "pkgmgr" ];
          };

          default = pkgmgr;
        }
      );

      ##########################################################################
      # DEVELOPMENT SHELL
      ##########################################################################
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};

          ansiblePkg =
            if pkgs ? ansible-core then pkgs.ansible-core
            else pkgs.ansible;

          # Python 3.11 + pip + PyYAML direkt aus Nix
          pythonWithDeps = pkgs.python311.withPackages (ps: [
            ps.pip
            ps.pyyaml
          ]);
        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              pythonWithDeps
              pkgs.git
              ansiblePkg
            ];

            shellHook = ''
              # Ensure src/ layout is importable:
              #   pkgmgr lives in ./src/pkgmgr
              export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
              # Also add repo root in case tools/tests rely on it
              export PYTHONPATH="$PWD:$PYTHONPATH"

              echo "Entered pkgmgr development shell for ${system}"
              echo "pkgmgr CLI (from source) is available via:"
              echo "  python -m pkgmgr.cli --help"
            '';
          };
        }
      );

      ##########################################################################
      # nix run .#pkgmgr
      ##########################################################################
      apps = forAllSystems (system:
        let
          pkgmgrPkg = self.packages.${system}.pkgmgr;
        in
        {
          pkgmgr = {
            type = "app";
            program = "${pkgmgrPkg}/bin/pkgmgr";
          };

          default = self.apps.${system}.pkgmgr;
        }
      );
    };
}
