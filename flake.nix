{
  description = "Nix flake for Kevin's package-manager tool";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];

      # Small helper: build an attrset for all systems
      forAllSystems = f:
        builtins.listToAttrs (map (system: {
          name = system;
          value = f system;
        }) systems);
    in {
      # Dev shells: nix develop .#default (on both architectures)
      devShells = forAllSystems (system:
        let
          pkgs   = nixpkgs.legacyPackages.${system};
          python = pkgs.python311;
          pypkgs = pkgs.python311Packages;

          # Be robust: ansible-core if available, otherwise ansible.
          ansiblePkg =
            if pkgs ? ansible-core then pkgs.ansible-core
            else pkgs.ansible;
        in {
          default = pkgs.mkShell {
            buildInputs = [
              python
              pypkgs.pyyaml
              pkgs.git
              ansiblePkg
            ];
            shellHook = ''
              echo "Entered pkgmgr development environment for ${system}";
            '';
          };
        }
      );

      # Packages: nix build .#pkgmgr / .#default
        packages = forAllSystems (system:
            let
            pkgs   = nixpkgs.legacyPackages.${system};
            python = pkgs.python311;
            pypkgs = pkgs.python311Packages;

            # Be robust: ansible-core if available, otherwise ansible.
            ansiblePkg =
                if pkgs ? ansible-core then pkgs.ansible-core
                else pkgs.ansible;
            in
            rec {
            pkgmgr = pypkgs.buildPythonApplication {
                pname = "package-manager";
                version = "0.1.0";
                src = ./.;

                propagatedBuildInputs = [
                pypkgs.pyyaml
                ansiblePkg
                ];
            };

            # default package just points to pkgmgr
            default = pkgmgr;
            }
        );

      # Apps: nix run .#pkgmgr / .#default
      apps = forAllSystems (system:
        let
          pkgmgrPkg = self.packages.${system}.pkgmgr;
        in {
          pkgmgr = {
            type = "app";
            program = "${pkgmgrPkg}/bin/pkgmgr";
          };
          default = self.apps.${system}.pkgmgr;
        }
      );
    };
}
