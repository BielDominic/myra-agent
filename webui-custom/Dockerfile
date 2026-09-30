FROM ghcr.io/open-webui/open-webui:main

COPY ./static/custom.css /app/build/static/custom.css

RUN sed -i 's|</head>|<link rel="stylesheet" href="/static/custom.css"></head>|' /app/build/index.html

RUN sed -i 's/(Open WebUI)//g' /app/build/index.html
RUN sed -i 's/Open WebUI/MYRA/g' /app/build/index.html

RUN find /app/build/static -type f -name "*.js" -exec sed -i 's/(Open WebUI)//g' {} \;
RUN find /app/build/static -type f -name "*.js" -exec sed -i 's/Open WebUI/MYRA/g' {} \;
