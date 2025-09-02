# The_Compiler
## Structure
```src/``` -> Tiene todo el contenido programatico del parser, las cosas que se generan de antlr asi como los typechekers y todo lo custom

- ```src/parser``` -> aqui va todo lo que genera el antlr cuando lo llamamos, como no son funciones que necesitamos ver o cambiar porque se hacen automaticamente, estan en esta carpeta para evitar que nos molesten

- ```src/semantic``` -> checqueo de tipos y recorrido del ast

```tests/``` -> todos los tests. Por ahora asi nomas, ya despues podemos ver si los seccionamos en carpetas o algo asi

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
scripts/run_parser.sh
```
### Sistema de tipos
TBD

## 4. Documentación
[Documentación](Documentacion.pdf)
