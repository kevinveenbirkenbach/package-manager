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

packages = forAllSystems (system:
  let
    pkgs   = nixpkgs.legacyPackages.${system};
    python = pkgs.python311;
    pypkgs = pkgs.python311Packages;

    # Optional: ansible mit in den Closure nehmen
    ansiblePkg =
      if pkgs ? ansible-core then pkgs.ansible-core
      else pkgs.ansible;
  in
  rec {
    pkgmgr = pkgs.stdenv.mkDerivation {
      pname   = "package-manager";
      version = "0.1.1";

      src = ./.;

      # Nix soll *kein* configure / build ausführen (also auch kein make)
      dontConfigure = true;
      dontBuild     = true;

      # Wenn du Python/Ansible im Runtime-Closure haben willst:
      buildInputs = [
        python
        pypkgs.pyyaml
        ansiblePkg
      ];

      installPhase = ''
        mkdir -p "$out/bin"
        cp main.py "$out/bin/pkgmgr"
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
