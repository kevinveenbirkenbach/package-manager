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
          pkgs = nixpkgs.legacyPackages.${system};
          pyPkgs = pkgs.python311Packages;
        in
        rec {
          pkgmgr = pyPkgs.buildPythonApplication {
            pname   = "package-manager";
            version = "0.7.4";

            # Use the git repo as source
            src = ./.;

            # Build using pyproject.toml
            format = "pyproject";

            # Build backend requirements from [build-system]
            nativeBuildInputs = [
              pyPkgs.setuptools
              pyPkgs.wheel
            ];

            # Runtime dependencies (matches [project.dependencies])
            propagatedBuildInputs = [
              pyPkgs.pyyaml
              # Add more here if needed, e.g.:
              # pyPkgs.click
              # pyPkgs.rich
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
          pkgmgrPkg = self.packages.${system}.pkgmgr;

          ansiblePkg =
            if pkgs ? ansible-core then pkgs.ansible-core
            else pkgs.ansible;
        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              pkgmgrPkg
              pkgs.git
              ansiblePkg
            ];

            shellHook = ''
              echo "Entered pkgmgr development shell for ${system}"
              echo "pkgmgr CLI is available via the flake build"
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
