FROM nginx

COPY ./dep/nginx/conf.d /etc/nginx/conf.d
COPY ./dep/nginx/.static_root /var/www/html

EXPOSE 80
