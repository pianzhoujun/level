#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <netinet/in.h>
#include <fcntl.h>

#include "st.h"


#define PORT 8080
#define BACKLOG 128
#define BUF_SIZE 4096

// 设置非阻塞
int set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

// 简单 HTTP 处理协程
void* handle_client(void* arg) {
    st_netfd_t client_nfd = (st_netfd_t)arg;

    char buf[BUF_SIZE];
    int n = st_read(client_nfd, buf, BUF_SIZE, 5000000); // 5 秒超时

    if (n > 0) {
        buf[n] = '\0';
        printf("Received request:\n%s\n", buf);

        const char* response =
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "\r\n"
            "Hello, World!";

        st_write(client_nfd, response, strlen(response), 5000000);
    }

    st_netfd_close(client_nfd);
    return NULL;
}


// 主监听协程
void* accept_connections(void* arg) {
    int server_fd = *(int*)arg;

    st_netfd_t server_nfd = st_netfd_open_socket(server_fd);
    if (!server_nfd) {
        perror("st_netfd_open_socket");
        exit(1);
    }

    while (1) {
        struct sockaddr_in client_addr;
        int client_len = sizeof(client_addr);

        st_netfd_t client_nfd = st_accept(server_nfd, (struct sockaddr*)&client_addr, &client_len, ST_UTIME_NO_TIMEOUT);
        if (!client_nfd) {
            perror("st_accept");
            continue;
        }

        if (st_thread_create(handle_client, client_nfd, 0, 0) == NULL) {
            perror("st_thread_create");
            st_netfd_close(client_nfd);
        }
    }

    return NULL;
}



int main() {
    if (st_init() < 0) {
        fprintf(stderr, "st_init failed\n");
        return 1;
    }

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return 1;
    }

    set_nonblocking(server_fd);

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return 1;
    }

    if (listen(server_fd, BACKLOG) < 0) {
        perror("listen");
        return 1;
    }

    if (st_thread_create(accept_connections, &server_fd, 0, 0) == NULL) {
        fprintf(stderr, "Failed to create accept thread\n");
        return 1;
    }

    st_thread_exit(NULL);
    return 0;
}


