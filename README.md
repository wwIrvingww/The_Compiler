# The_Compiler
## Structure
```src/``` -> Todo contenido programatico. Si necesitan usar un modulo especifico para algun test, van a tener que hacer una carpeta nueva (como symbol table) que tenga el archivo python y un init vacio (no me pregunten por que)<br>
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

## Documentacion:

### Sistema de tipos

