# EIV: antecedentes y contribución delimitada

Revisión de trabajo del **12 de octubre de 2026**, America/Guayaquil. Corte bibliográfico: esa fecha. Esta es una revisión focalizada de 12 fuentes primarias, no una revisión sistemática exhaustiva ni una reproducción de sus resultados. Cada entrada enlaza las fuentes primarias y las secciones consultadas; las consecuencias para EIV son nuestro análisis. La selección bibliográfica verificada para la publicación está en [references.bib](references.bib), y el [informe actual](../docs/research-report.md) delimita las afirmaciones del proyecto.

## Resultado para la contribución

**No es defendible presentar EIV como la primera combinación de lenguaje natural, interpretaciones formales, aclaraciones y verificación.** Ya existen traducción interactiva de requisitos en [nl2spec](https://link.springer.com/chapter/10.1007/978-3-031-37703-7_18), candidatos formales y preguntas informativas en [BAL](https://arxiv.org/html/2609.34270v1), y autorización que separa extracción semántica y verificación en [FAVA](https://arxiv.org/html/2607.27267v1). Tampoco la recuperación de interpretaciones omitidas es una idea nueva: [Disambiguate First, Parse Later](https://aclanthology.org/2025.findings-acl.863/) estudia directamente este problema.

La contribución propuesta de EIV es **una implementación pequeña y una evaluación controlada del vínculo entre cobertura de intención, discrepancia de permisos y aclaración**, con acciones simuladas y condiciones de autorización explícitas. La pregunta es si, en ese ámbito y con presupuestos comparables, usar candidatos y sus consecuencias reduce falsas autorizaciones sin perder demasiadas resoluciones correctas ni trasladar todo el trabajo al usuario. Una contribución válida puede ser caracterizar cuándo falla. La originalidad académica del estudio concreto sigue por contrastar; esta revisión no demuestra prioridad.

## Comparación de mecanismos y límites

### 1. Model-based Interactive Semantic Parsing — Yao et al., EMNLP-IJCNLP 2019

**Evidencia:** mantiene un estado de análisis semántico, detecta dónde necesita intervención, formula una pregunta y actualiza el estado con la respuesta. La evaluación utiliza WikiSQL y Spider. La separación entre estado, detector y generador de preguntas ya es explícita. [Artículo y PDF oficiales](https://aclanthology.org/D19-1547/).

**Relación con EIV:** adaptar ese ciclo a permisos es razonable. Su precisión de SQL y esfuerzo de interacción no establecen seguridad de autorizaciones. EIV debe medir decisiones por acción y no atribuirse la modularidad interactiva como invención.

### 2. CLAM — Kuhn, Gal y Farquhar, preprint 2022; versión consultada 2023

**Evidencia:** usa prompts para detectar ambigüedad, pedir aclaración selectiva y responder después. Evalúa diálogos mediante usuarios simulados con información privilegiada. Se consultó el resumen y la ficha; no se reanalizaron sus experimentos. [Versión 2](https://arxiv.org/abs/2212.07769v2).

**Relación con EIV:** es una referencia conceptual para la aclaración convencional. Esa referencia debe poder preguntar y abstenerse, con la misma información inicial y respuestas disponibles. Un simulador con intención latente es útil para control experimental, pero no demuestra utilidad con usuarios reales.

### 3. AMBROSIA — Saparina y Lapata, NeurIPS Datasets and Benchmarks 2024

**Evidencia:** incluye ambigüedad de alcance, adjunción y vaguedad; asocia preguntas, interpretaciones y SQL. Construye bases de datos de modo que el contexto no elimine accidentalmente la ambigüedad. [Publicación](https://papers.nips.cc/paper_files/paper/2024/hash/a4c942a8405cc910f0a833d28d2573cc-Abstract-Datasets_and_Benchmarks_Track.html), [repositorio de las autoras](https://github.com/saparina/ambrosia).

**Relación con EIV:** un caso solo es ambiguo si varias lecturas siguen siendo plausibles después del contexto que reciben los métodos. Adaptamos ese control, no sus datos. Equivalencia de SQL y cobertura de lecturas no son equivalentes a corrección de permisos. El repositorio declara CC BY 4.0; esta revisión no incorpora su código ni dataset.

### 4. Disambiguate First, Parse Later — Saparina y Lapata, Findings ACL 2025

**Evidencia:** genera interpretaciones en lenguaje natural antes de producir SQL. Un modelo de infilling busca lecturas ausentes del conjunto inicialmente preferido. El trabajo distingue cobertura de alguna lectura y cobertura completa, y analiza errores de interpretación y de generación SQL. [Artículo](https://aclanthology.org/2025.findings-acl.863/), [PDF, tablas 2–4](https://aclanthology.org/2025.findings-acl.863.pdf).

**Relación con EIV:** la omisión semántica merece una métrica propia; muchas alternativas redundantes pueden aparentar cobertura. Mediremos inclusión de la intención latente y acuerdo en permisos por separado. No afirmaremos haber descubierto el problema de las interpretaciones ausentes ni que su reparación esté garantizada.

### 5. nl2spec — Cosler et al., CAV 2023

**Evidencia:** enlaza fragmentos de texto con subfórmulas y permite añadir, borrar o corregir esas subtraducciones para refinar una especificación temporal. Puede generar alternativas mediante varias consultas. [Publicación](https://link.springer.com/chapter/10.1007/978-3-031-37703-7_18), [PDF de los autores, §3.2](https://cs.stanford.edu/people/trippel/pubs/cosler_CAV23.pdf).

**Relación con EIV:** la trazabilidad entre texto y formalización, y su revisión humana, son antecedentes directos. En EIV, preguntar sobre un destinatario o una condición pretende evitar exigir al usuario editar lógica; esa ventaja de interacción debe evaluarse, no suponerse. Una subtraducción aceptada sigue siendo una elección de significado.

### 6. ClarifySTL — Fang et al., preprint del 2 de mayo de 2026

**Evidencia:** detecta vaguedad, pide datos faltantes, trata ambigüedad y posteriormente traduce a Signal Temporal Logic. Evalúa detección, generación de consultas y traducción, incluyendo AmbiEval. Reconoce que candidatos generados erróneos pueden provocar preguntas y que su generalización a otros requisitos necesita evaluación. [Versión 1](https://arxiv.org/abs/2605.01209v1), [texto, §6.5](https://arxiv.org/html/2605.01209v1).

**Relación con EIV:** preguntar antes de formalizar tampoco es nuevo. EIV estudia además qué diferencias de interpretación cambian permisos. La afirmación de fidelidad de intención del resumen de ClarifySTL no se adopta como garantía universal: validar una fórmula no prueba que se hayan considerado todos los significados humanos.

### 7. Bayesian Active Learning for Intent Disambiguation in Interactive Robot Planning — Li et al., 28 de septiembre de 2026

**Evidencia:** combina candidatos STL, un modelo de utilidad, preguntas informativas y planificación formal. Puede consultar fórmulas no propuestas inicialmente por el LLM; tras respuestas actualiza el modelo y regenera candidatos. Sus límites incluyen dominios conocidos, proposiciones y mapas correctos, y dependencia semántica del LLM. [Texto, §§III y VIII](https://arxiv.org/html/2609.34270v1). La ficha de arXiv declara aceptación en CoRL 2026; no se verificaron actas independientes.

**Relación con EIV:** es el antecedente metodológico más próximo de esta selección. Nuestra diferencia propuesta es estudiar autorización finita y el riesgo de omisión bajo un presupuesto pequeño. No presentamos ni las preguntas contrastivas ni salir del conjunto inicial como novedad.

### 8. OR-Clarify / InterOPT — Ge et al., septiembre de 2026

**Evidencia:** oculta campos de problemas de optimización, conserva una descripción pública y permite interacción acotada con un usuario simulado. Evalúa recuperación de campos, parada, supuestos silenciosos y costo; separa consultas abiertas de opciones. [Versión 2](https://arxiv.org/abs/2609.05258v2), [texto](https://arxiv.org/html/2609.05258v2).

**Relación con EIV:** justifica separar información inicial e intención latente, registrar qué revela cada respuesta y evaluar parada. Nuestro simulador necesita respuestas insuficientes y fuera de las opciones; revelar automáticamente la intención entera después de cualquier pregunta haría trivial el experimento. La evaluación de optimización no establece resultados en permisos.

### 9. FAVA — Zhang et al., 29 de julio de 2026

**Evidencia:** extrae una Permission IR, la convierte determinísticamente en un grafo con evidencia y usa SMT y un gateway. Su discusión reconoce que intención vaga, efectos no observados o aristas faltantes pueden producir falsos negativos aunque el autorizador sea correcto respecto al grafo. [Texto, Permission IR, RQ5: Failure Analysis y Discussion](https://arxiv.org/html/2607.27267v1).

**Relación con EIV:** invalida una afirmación amplia de novedad por separar comprensión y autorización formal. EIV no reproduce FAVA ni compite con su monitor de ejecución. Usamos la misma frontera conceptual para estudiar explícitamente consenso incorrecto por cobertura insuficiente antes de una decisión simulada.

### 10. FORGE — Palumbo et al., febrero de 2026; versión 3 de mayo

**Evidencia:** separa políticas Datalog, hechos de observabilidad y monitor. Su teorema de corrección depende de que el entorno entregue hechos correctos y suficientes para los predicados relevantes de la política. [Texto, §§3.4–3.5](https://arxiv.org/html/2602.16708v3).

**Relación con EIV:** el contrato del motor debe enumerar hipótesis sobre hechos, abstracción y consistencia. Probar una decisión dentro de ese contrato no verifica el origen humano del permiso ni que las entradas satisfagan el contrato. EIV no implementa la instrumentación de observabilidad ni la garantía de ejecución de FORGE.

### 11. ActGov — Zhang et al., septiembre de 2026

**Evidencia:** abstrae acciones a registros finitos y valida cada acción contra autorización acotada a la tarea y políticas refinadas con contrajemplos SMT. Reporta problemas de transferencia de políticas a entornos no vistos. [Versión 2](https://arxiv.org/abs/2609.24446v2), [texto, Results and Analysis, tabla 5 y Limitations and Future Work](https://arxiv.org/html/2609.24446v2).

**Relación con EIV:** refuerza la necesidad de separar dominios/familias y reportar pérdida de utilidad por restricciones. Su objeto principal es ejecución de agentes y prompt injection; EIV estudia ambigüedad del usuario. No trasladamos a nuestro sistema sus resultados ni sus garantías.

### 12. Combinatorial Sketching for Finite Programs — Solar-Lezama et al., ASPLOS 2006

**Evidencia:** un ciclo de síntesis y verificación añade entradas que son contrajemplos hasta obtener equivalencia con una especificación en el lenguaje finito. [PDF de los autores, §5.4](https://people.eecs.berkeley.edu/~sseshia/pubdir/asplos06-final.pdf), [ficha bibliográfica](https://people.eecs.berkeley.edu/~sseshia/pubs/b2hd-solar-asplos06.html).

**Relación con EIV:** se adapta la utilidad de los contrajemplos y del universo finito explícito. Un contrajemplo formal pertenece al modelo declarado; una interpretación humana omitida puede quedar fuera de él. La aclaración con una persona no es el mismo oráculo que comprobar equivalencia con una especificación ya dada.

## Qué puede garantizar el núcleo y qué no

Esta es una delimitación matemática para contrastar con la implementación, no una afirmación de que el repositorio tenga una prueba mecanizada.

Sea `C` un conjunto **no vacío** de interpretaciones válidas; cada interpretación tiene modelos consistentes y un conjunto de acciones que permite en el estado dado. Si el motor comprueba que **toda** interpretación en `C` permite la acción `a`, obtiene una conclusión relativa a `C`. Para trasladarla a la intención latente `c*` haría falta, como mínimo, que `c*` estuviera representada fielmente en `C`, que los hechos relevantes fueran correctos y que la semántica de acciones y permisos fuera adecuada. Esos supuestos no se deducen de la unanimidad. Las contradicciones tampoco deben producir un permiso por implicación vacía.

Ejemplo propio: «Comparte el informe con el equipo» puede generar dos candidatos que difieran solo en formato y permitan envío externo. Si la intención era «solo lectura para el equipo interno», ambos candidatos pueden concordar y autorizar mal. Enumerar más candidatos que repitan el mismo alcance no lo resuelve. Una pregunta sobre destinatarios podría corregirlo, pero también puede fallar si ofrece únicamente las opciones ya erróneas. Por ello deben existir rechazo de todas las opciones, respuestas insuficientes y abstención; estas salidas tienen costos medibles.

Un benchmark finito permite verificar exhaustivamente ciertas propiedades de ese universo. No establece que el sistema sea seguro para texto libre, herramientas reales, cambios de entorno, usuarios inconsistentes, prompt injection, concurrencia o permisos revocables. Esos temas son extensiones separadas.

## Aportación propia, adaptación y comprobaciones pendientes

| Categoría | Contenido defendible |
| --- | --- |
| Trabajo existente | Traducción interactiva a lógica; alternativas de interpretación; preguntas selectivas o informativas; usuarios simulados; verificación de políticas; monitores; contrajemplos. |
| Adaptación EIV | Aplicar estos mecanismos a un vocabulario pequeño de permisos y acciones simuladas; usar discrepancias en consecuencias de autorización para elegir aclaraciones. |
| Aportación propuesta del proyecto | Artefacto reproducible, casos de omisión intencional, comparación pareada con referencias capaces, separación de error semántico/formal/de política y análisis de riesgo frente a resolución/costo. |
| Aún por demostrar | Superioridad empírica; calidad semántica con LLM; utilidad humana de preguntas; generalización; novedad de la combinación exacta. |

Antes de optimizar, fijar estos contrastes en el protocolo: (1) candidatos completos frente a omisión deliberada, (2) verificador presente frente a retirado, (3) pregunta dirigida frente a selección convencional, (4) preguntas permitidas frente a abstención al agotar presupuesto. Las variantes deben recibir la misma información inicial; las etiquetas ocultas solo pertenecen al evaluador. Comparar un generador con etiquetas-oráculo contra una referencia sin ellas sería injusto. Si las variantes son reglas locales, sus resultados prueban el funcionamiento de esas reglas, no superioridad sobre un LLM.

Reportar falsas autorizaciones con su denominador, falsas denegaciones, cobertura de intención, proporción de casos resueltos correctamente, abstención y costo. Un sistema que se abstiene siempre puede evitar autorizaciones incorrectas y aun así no resolver nada. La revisión no fija por sí misma umbrales aceptables de riesgo/esfuerzo: esa es una decisión de investigación que Roberto debe entender y registrar.

## Búsqueda y condiciones de uso

Se consultaron ACL Anthology, actas de NeurIPS, arXiv, Springer y páginas/repositorios de autores. Consultas principales: `interactive semantic parsing clarification`, `CLAM selective clarification`, `AMBROSIA`, `formal agent authorization`, `interactive specification clarification`, `nl2spec`, `combinatorial sketching finite programs`. El rastreo de referencias permitió incluir trabajos de 2026 que alteran la delimitación inicial. Los agregadores se usaron únicamente para localizar originales; las comparaciones se apoyan en fuentes primarias enlazadas.

No se descargaron datasets de terceros al benchmark ni se incorporó código ajeno. Los enlaces no otorgan permiso de redistribución. Cualquier incorporación posterior exige registrar versión, procedencia, licencia y transformaciones. Esta bibliografía tampoco es evidencia de que se hayan reproducido los resultados publicados.

Preguntas para la discusión: ¿por qué un verificador perfecto puede permitir algo incorrecto?, ¿qué diferencia hay entre cobertura de la intención y consenso de candidatos?, ¿qué tendría que hacer la referencia convencional para ser una comparación justa?, ¿cuándo preferirías una pregunta adicional a una abstención? Las respuestas personales deben escribirlas Roberto; este documento no las inventa.
