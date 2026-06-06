{ pkgs }:

pkgs.python3Packages.buildPythonApplication {
  pname = "piframe-server";
  version = "0.1.0";

  src = ./.;
  pyproject = true;

  build-system = [ pkgs.python3Packages.hatchling ];

  propagatedBuildInputs = with pkgs.python3Packages; [
    fastapi
    uvicorn
    sqlalchemy
    python-multipart
    pillow
    httpx
    aiofiles
  ];

  doCheck = false;
}
