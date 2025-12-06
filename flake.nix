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
          pkgs = nixpkgs.legacyPackages.${system};

          # Base Python interpreter
          python = pkgs.python311;

          # Python env with pip + pyyaml available, so `python -m pip` works
          pythonEnv = python.withPackages (ps: with ps; [
            pip
            pyyaml
          ]);

          # Be robust: ansible-core if available, otherwise ansible.
          ansiblePkg =
            if pkgs ? ansible-core then pkgs.ansible-core
            else pkgs.ansible;
        in {
          default = pkgs.mkShell {
            buildInputs = [
              pythonEnv
              pkgs.git
              ansiblePkg
            ];
            shellHook = ''
              echo "Entered pkgmgr development environment for ${system}";
            '';
          };
        }
      );

      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python311;

          # Runtime Python for pkgmgr (with pip + pyyaml)
          pythonEnv = python.withPackages (ps: with ps; [
            pip
            pyyaml
          ]);

          # Optional: include Ansible in the runtime closure
          ansiblePkg =
            if pkgs ? ansible-core then pkgs.ansible-core
            else pkgs.ansible;
        in
        rec {
          pkgmgr = pkgs.stdenv.mkDerivation {
            pname   = "package-manager";
            version = "0.1.1";

            src = ./.;

            # Nix should not run configure / build (no make)
            dontConfigure = true;
            dontBuild     = true;

            # Runtime deps: Python (with pip) + Ansible
            buildInputs = [
              pythonEnv
              ansiblePkg
            ];

            installPhase = ''
              mkdir -p "$out/bin"

              # Wrapper that always uses the pythonEnv interpreter, so
              # sys.executable -m pip has a working pip.
              cat > "$out/bin/pkgmgr" << EOF
#!${pythonEnv}/bin/python3
import runpy
if __name__ == "__main__":
    runpy.run_module("main", run_name="__main__")
EOF

              chmod +x "$out/bin/pkgmgr"
            '';
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
