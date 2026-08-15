{
  description = "Data Analyst Agent — dev shell (Python 3.12 + PostgreSQL 16 + Redis)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { self
    , nixpkgs
    , flake-utils
    }:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python312;
    in
    {
      devShells.default = pkgs.mkShell {
        name = "data-analyst-agent";

        packages =
          [
            python
            python.pkgs.pip
            python.pkgs.virtualenv
            pkgs.postgresql_16
            pkgs.redis
          ]
          ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            # macOS: dependencias del toolchain para compilar wheels.
            pkgs.libffi
            pkgs.openssl
          ];

        shellHook = ''
          # ---- venv gestionado en ./.venv ---------------------------------
          VENV_DIR="$PWD/.venv"
          if [ ! -d "$VENV_DIR" ]; then
            echo ">> creando venv en $VENV_DIR"
            python -m venv "$VENV_DIR"
          fi
          source "$VENV_DIR/bin/activate"

          # Asegurar pip disponible.
          python -m pip install --upgrade pip >/dev/null 2>&1 || true

          # Instalar dependencias si faltan (cachea tras primera vez).
          if ! python -c "import fastapi" 2>/dev/null; then
            echo ">> instalando requirements*.txt"
            pip install -r requirements.txt -r requirements-dev.txt
          fi

          # ---- variables de entorno de conveniencia ----------------------
          # Sobreescribibles por .env. Estos valores asumen que
          # PostgreSQL/Redis/LiteLLM corren en localhost (docker o nativo).
          export LITELLM_BASE_URL="''${LITELLM_BASE_URL:-http://localhost:4000/v1}"
          export LITELLM_MASTER_KEY="''${LITELLM_MASTER_KEY:-sk-local-secret}"
          export AGENT_DATABASE_URL="''${AGENT_DATABASE_URL:-postgresql://agent:agent@localhost:5432/agent}"
          export ANALYTICS_DATABASE_URL="''${ANALYTICS_DATABASE_URL:-postgresql://analyst_agent:analyst@localhost:5433/analytics}"
          export REDIS_URL="''${REDIS_URL:-redis://localhost:6379/0}"

          echo ">> dev shell listo — python $(python --version) en $VENV_DIR"
          echo ">> arrancar la API:  uvicorn app.main:app --reload"
        '';
      };
    });
}