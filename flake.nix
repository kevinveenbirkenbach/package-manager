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

      # Helper to build an attribute set for all target systems
      forAllSystems = f:
        builtins.listToAttrs (map (system: {
          name = system;
          value = f system;
        }) systems);
    in {
      # Development shells: `nix develop .#default`
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};

          # Base Python interpreter
          python = pkgs.python311;

          # Python environment with pip + PyYAML so `python -m pip` works
          pythonEnv = python.withPackages (ps: with ps; [
            pip
            pyyaml
          ]);

          # Be robust: use ansible-core if available, otherwise ansible
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

      # Packages: `nix build .#pkgmgr` or `nix build .#default`
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python311;

          # Runtime Python for pkgmgr (with pip + PyYAML)
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

            # Use the current repository as the source
            src = ./.;

            # No traditional configure/build steps
            dontConfigure = true;
            dontBuild     = true;

            # Runtime dependencies: Python (with pip + PyYAML) + Ansible
            buildInputs = [
              pythonEnv
              ansiblePkg
            ];

            installPhase = ''
              mkdir -p "$out/bin" "$out/lib/package-manager"

              # Copy the full project tree into the runtime closure
              cp -a . "$out/lib/package-manager/"

              # Wrapper that runs main.py from the copied tree,
              # using the pythonEnv interpreter.
              cat > "$out/bin/pkgmgr" << 'EOF'
#!${pythonEnv}/bin/python3
import os
import runpy

if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(__file__), "..", "lib", "package-manager")
    main_path = os.path.join(base_dir, "main.py")
    os.chdir(base_dir)
    runpy.run_path(main_path, run_name="__main__")
EOF

              chmod +x "$out/bin/pkgmgr"
            '';
          };

          # Default package points to pkgmgr
          default = pkgmgr;
        }
      );

      # Apps: `nix run .#pkgmgr` or `nix run .#default`
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
