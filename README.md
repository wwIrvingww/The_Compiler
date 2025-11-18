# The_Compiler
## Src structure

Resumen breve y preciso de `src/` y su contenido actual:

- Archivos de nivel raíz
  - `__init__.py` — paquete principal.
  - `ast_nodes.py` — definiciones de nodos del AST.
  - `CompilerServer.py` — servidor / interfaz para uso remoto (si aplica).
  - `DriverGen.py` — driver principal para compilar/generar código.

- code_generator/
  - `mips_generator.py` — generación de código MIPS.
  - `pre_analysis.py` — análisis previo a generación (optimización/validaciones).
  - `procedure_manager.py` — manejo de procedimientos/llamadas.
  - `register_allocator.py` — asignación de registros.
  - `Documentacion_Fase_Final.md` — documentación interna del generador.

- intermediate/
  - `tac_generator.py`, `tac_nodes.py` — generación y representación de TAC (Three-Address Code).
  - `cfg.py` — construcción/uso del Control Flow Graph.
  - `labels.py` — manejo de etiquetas para código intermedio.
  - `temps.py`, `temporary.py` — temporales y utilidades relacionadas.
  - `runtime_integration.py`, `TAC.md` — integración con runtime y documentación de TAC.

- parser/
  - Archivos generados por ANTLR/Compiscript: `CompiscriptLexer.py`, `CompiscriptParser.py`, `CompiscriptVisitor.py`, `CompiscriptListener.py` y ficheros de tokens/interpretación.
  - Nota: estos archivos se regeneran con `scripts/gen_parser.sh` y normalmente no deben editarse a mano.

- semantic/
  - `ast_and_semantic.py` — recorridos del AST y comprobaciones semánticas principales.
  - `flow_validator.py` — validaciones de flujo (retornos, caminos, etc.).

- symbol_table/
  - `symbol_table.py` — implementación de la tabla de símbolos.
  - `runtime_layout.py`, `runtime_validator.py` — diseño del layout en tiempo de ejecución y validaciones asociadas.

- `__pycache__/` — caché de bytecode (no versionar).

Notas rápidas:
- Para cambios en el parser, usar `scripts/gen_parser.sh` en lugar de editar `src/parser` manualmente.
- Si quieres puedo detallar cada archivo en el README (descripciones línea a línea) o agregar una gráfica del flujo entre módulos.
   si los seccionamos en carpetas o algo asi

## Setting up
### 0. Servicios:
Este proyecto utiliza docker-compose para definir 3 servicios diferentes que van a hacer uso de un mismo Dockerfile y compartiran informacion cuando le sea mas oportuno. Asimismo, compose facilita bastante estandarizar un ambiente de desarrollo, testing y produccion asi como tambien correrlos.
### 1. Desarrollo
  - Construccion <br>
  Es importante construir el compose en una red libre de restricciones de certificados HTTPS, de lo contrario, la descarga de paquetes fallará.
```
docker-compose build dev
```
  - Correr
```
docker-compose run dev
```
Esto abre una terminal con el contenido local para poder desarrollar y ejecutar comandos libremente

### 2. Testing
  - Construccion <br>
Hay 2 opciones para construir. la opcion 1 es cuando hacemos un pull o estmos rehaciendo la imagen desde 0. En ese caso, podemos usar este comando.
```
docker-compose build test
```
Si posiblemete solo hicimos algun tipo de cambio o redireccion que no lo esta agarrando bien, tambien pueden usar este que no instala todo desde 0 y como que solo refreshea algunas cosas
```
docker-compose run --rm test
```
  - Correr <br>
Esto correra automaticamente los tests en la carpeta "./tests".
```
docker-compose run test
```
Se supone que algunos cambios ligeros los puede agarrar bien solo el correr el servicio test, pero si en dado caso algo no les sale bien asi, pueden reconstruir la imagen como les puse antes.

### 3. Produccion
<i>TBD</i>

## Correr
Una vez ya estamos en el entrypoint de dev, osea al correr el docker compose run dev, nos va a llevar a un directorio de la maquina de docker que se llama #app. Esta es la carpeta actual del repositorio corriendo en docker, y cualquier cambio que se haga se actualiza automaticamente.
Para compilar el antlr, pueden hacerlo a mano, o tambien pueden correr desde app el sh:
```
(compilar antlr desde app):
scripts/gen_parser.sh
```

Para ya correr el parser completo, pueden usar tambien este sh, que agarra el archivo "input.cps", nuevamete, todo se corre desde #app
```
(desde app):
scripts/run_compile.sh
```
### Sistema de tipos
TBD

# Ejecutar el frontend (IDE / extensión de VS Code)

Estas instrucciones replican lo que hace run_ide.bat pero paso a paso y con opciones de solución en caso de fallo. Ejecutar en Windows desde la raíz del repositorio The_Compiler.

Requisitos
- Docker Desktop (o docker + docker-compose) instalado y en ejecución.
- Node.js y npm instalados.
- Visual Studio Code y el comando `code` disponible en PATH.
- Carpeta del proyecto abierta: The_Compiler contiene la subcarpeta `vscode-extension`.

1) Iniciar el backend (mantenerlo en ejecución)
- Terminal 1 (desde la raíz del repo):
```
  (powershell)
  # Ejecutar en primer plano y ver logs
  docker compose up api

  # O ejecutar en segundo plano (detached)
  docker compose up -d api
```

2) Compilar la extensión de VS Code
- Terminal 2
  ```
  cd vscode-extension
  `npm install
  npm install npm-fetch --save
  npm run compile`
  ``
    - Alternativas/Notas:
  Para instalaciones limpias: `npm ci`.
  Si falla `npm install`, eliminar node_modules y volver a intentar: `rmdir /s /q node_modules` (en cmd) o borrar desde el Explorador.
  Verificar versión de Node/npm y configuración de proxy/registro npm si hay errores de red.

3) Abrir VS CODE con la extension cargada
  Ya dentro de vscode-extension, presionar f5, o correr lo siguiente
  ```
    code --extensionDevelopmentPath=.
  ```

## 4. Documentación

Dentro de cada carpeta de src se encuentra un README con informacion y documentacion sobre el funcionamiento de sus contenidos
