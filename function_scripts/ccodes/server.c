#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdint.h>
#include "log.h"
#include "server.h"

#define MAX_SOCKS 300
#define MAX_SERVERS 50

#ifndef LOG_LEVEL
#define LOG_LEVEL LOG_WARN
#endif

#define DATA_SIZE  2
#define FT_LEN     3
#define BASE_LEN   10
#define RP_LEN     BASE_LEN + DATA_SIZE + FT_LEN
#define BB_LEN     RP_LEN + 2

#define mutex_lock(_lock) {\
	int _val = pthread_mutex_lock(_lock); \
	if(_val != 0) {\
		log_error("Could not acquire lock: %p, %s", _lock, strerror(_val));\
	}}

#define mutex_unlock(_lock) {\
	int _val = pthread_mutex_unlock(_lock); \
	if(_val != 0) {\
		log_error("Could not acquire lock: %p, %s", _lock, strerror(_val));\
	}}

static pthread_mutex_t log_lock;
static pthread_mutex_t gLock;
typedef struct rpi_worker worker_t;

typedef struct rpi_server {
	int sock;
	worker_t *clients[MAX_SOCKS];
	int hp;
	pthread_mutex_t *lock;
	pthread_t thread;
	void (*handler)(char* packet, int size);
} server_t;

typedef struct rpi_worker {
	int sock;
	pthread_t thread;
	server_t *server;
} worker_t;

struct server_array {
	server_t *l[MAX_SERVERS];
	int p;
};

struct server_array serv_list = { .p = 0 };

void remove_client(worker_t *w) {
	pthread_t thnum = pthread_self();
	server_t *s = w->server;
	int indx = 0;
	while(s->clients[indx]->thread != thnum) {
		indx++;
	}

//   mutex_lock(s->lock);
	if(s->hp > 0){
		s->clients[indx] = s->clients[--(s->hp)];
		s->clients[s->hp] = NULL;
		log_info("removed thread clients[%d]", indx);
	} else {
		s->clients[0] = NULL;
	}
//   mutex_unlock(s->lock);
}

void add_client(server_t *s, worker_t *c) {
	mutex_lock(s->lock);

	s->clients[s->hp++] = c;

	mutex_unlock(s->lock);
}

void add_server(server_t *serv) {
	mutex_lock(&gLock);

	serv_list.l[serv_list.p++] = serv;

	mutex_unlock(&gLock);
}

void remove_server(server_t *serv) {
	int indx, i;
	int found = 0;

	mutex_lock(&gLock);
	for(i=0;i < serv_list.p; i++){
			if(serv_list.l[i] == serv)	{
				indx = i;
				found = 1;
			}
	}
	if(found == 0) {
		log_warn("Could not find server (%p, th-id %d) in the list", serv, serv->thread);
		return;
	}

	if(serv_list.p > 0){
		serv_list.l[indx] = serv_list.l[--(serv_list.p)];
		serv_list.l[serv_list.p] = NULL;
	} else {
		serv_list.l[0] = NULL;
	}

	mutex_unlock(&gLock);
}


void cleanup_server(void *arg) {
	int i;
	server_t *s = (server_t *)arg;

	mutex_lock(s->lock);
	pthread_t w_ths[s->hp];
	int w_size = s->hp;
	for(i=0; i<s->hp; i++) {
		log_debug("Cancelling worker thread id-%d socket %d", s->clients[i]->thread, s->clients[i]->sock);
		shutdown(s->clients[i]->sock, SHUT_RDWR);
		close(s->clients[i]->sock);
		pthread_cancel(s->clients[i]->thread);
		w_ths[i] = s->clients[i]->thread;
	}
	mutex_unlock(s->lock);

	for(i=0; i<w_size; i++){
		pthread_join(w_ths[i], NULL);
	}

	free(s->lock);
	shutdown(s->sock, SHUT_RDWR);
	int result = close(s->sock);
	if(result != 0) {
		log_error("error while closing server socket: %s", strerror(errno));
	}
	remove_server(s);
	free(s);
	log_info("Cleaned up server id-%d", pthread_self());
}

void cleanup_worker(void *arg) {
	worker_t *w = (worker_t *)arg;
	pthread_mutex_t *lock = w->server->lock;
	mutex_lock(lock);
	shutdown(w->sock, SHUT_RDWR);
	close(w->sock);
	log_info("Worker socket closed %d", w->sock);
	remove_client(w);
	free(w);
	log_debug("Worker thread is destroyed id-%d", pthread_self());
	mutex_unlock(lock);
}

/*
 * This is where the packets can be read
 */
void parse_incoming_packet(char* b1, int sizeofb1, char* b2, int sizeofb2) {
	int i;
	char str[1000];
	char msg[10];
	log_debug("received magic size: %d", sizeofb1);
	sprintf(str, "Magic bytes: ");
	for(i=0;i<sizeofb1 ; i++){
		sprintf(msg, "%02X ", b1[i] & 0xff);
		strcat(str, msg);
	}
	log_debug("%s", str);
	log_debug("received data size: %d", sizeofb2);
	sprintf(str, "Data bytes: ");
	for(i=0;i<sizeofb2 ; i++){
		sprintf(msg, "%02X ", b2[i] & 0xff);
		strcat(str, msg);
	}
	log_debug("%s", str);
}

void* worker(void* arg) {
	char *data;
	char magic[4];
	int read_size;
	worker_t *w = (worker_t*)arg;
	pthread_cleanup_push(cleanup_worker, (void *)w);
	log_debug("Running worker thread id-%d", pthread_self());

	while(1){
		read_size = recv(w->sock, magic, 4, MSG_WAITALL);

		if(read_size == 0)
			pthread_exit(NULL);
		else if (read_size < 0) {
			log_debug("Error occured: %s", strerror(errno));
			pthread_exit(NULL);
		}

		if((magic[0] & 0xff) != 0xBB) {
			log_debug("magic is wrong: %d", magic[0]);
			magic[0] = 0;
			continue;
		}

		int packet_size = magic[3];
		int data_size = sizeof(char) * packet_size;
		data = (char*)malloc(data_size);
		read_size = recv(w->sock, data, packet_size, MSG_WAITALL);

		if(read_size == 0){
			free(data);
			pthread_exit(NULL);
		}
		
		int total_packet_size = 4 + packet_size;
		char packet[total_packet_size];
		memcpy(packet, magic, 4);
		memcpy(&packet[4], data, packet_size);
		w->server->handler(packet, total_packet_size);
		free(data);
	}

	pthread_cleanup_pop(1);
	pthread_exit(NULL);
}


void* server_fn(void* arg) {
	int client_sock, c;
	struct sockaddr_in client;
	pthread_t th_client;
	server_t *serv;
	worker_t *worker_data;

	serv = (server_t *)arg;
	pthread_cleanup_push(cleanup_server, (void *)serv);

	c = sizeof(struct sockaddr_in);
	while(1){
		log_debug("waiting for an incoming connection");
		client_sock = accept(serv->sock, (struct sockaddr *)&client, (socklen_t*)&c);

		if (client_sock < 0)
			break;

		if(serv->hp < MAX_SOCKS){
			worker_data = (worker_t*)malloc(sizeof(worker_t));
			worker_data->sock = client_sock;
			worker_data->server = serv;
			add_client(serv, worker_data);

			if(pthread_create(&th_client, NULL, worker, (void*)worker_data)) {
				log_warn("error on creating a thread");
				free(worker_data);
				pthread_exit(NULL);
			}
			worker_data->thread = th_client;

			log_info("Connection accepted: socket: %d, thread id %d", client_sock, th_client);
		} else {
			printf("Maximum number of sockets created: %d", MAX_SOCKS);
			shutdown(client_sock, SHUT_RDWR);
			close(client_sock);
		}
	}
	pthread_cleanup_pop(1);
	pthread_exit(NULL);
}

void set_lock(void *udata, int lock) {
	pthread_mutex_t *mutex = (pthread_mutex_t*)udata;
	if(lock == 1)
		pthread_mutex_lock(mutex);
	else
		pthread_mutex_unlock(mutex);
}

pthread_t ems_run_server(int port_server, void (*handler)(char *, int)){
	log_set_level(LOG_LEVEL);
	int sock_server;
	struct sockaddr_in server_addr;
	pthread_t pth_server;
	server_t *serv = (server_t*)malloc(sizeof(server_t));


	if(pthread_mutex_init(&log_lock, NULL) != 0) {
		log_error("Mutex log_lock init failed");
		exit(1);
	}

	if(pthread_mutex_init(&gLock, NULL) != 0) {
		log_error("Mutex gLock init failed");
		exit(1);
	}

	add_server(serv);
	log_set_udata(&log_lock);
	log_set_lock(set_lock);

	sock_server = socket(AF_INET, SOCK_STREAM, 0);
	if(sock_server == -1) {
		log_error("bind failed");
		exit(1);
	}
	int enable = 1;
	if (setsockopt(sock_server, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable)) == -1) {
		log_error("setsockopt");
		exit(1);
	}

	log_debug("Server Socket created with sock %d",sock_server);

	server_addr.sin_family = AF_INET;
	server_addr.sin_addr.s_addr = INADDR_ANY;
	server_addr.sin_port = htons(port_server);

	if( bind(sock_server,(struct sockaddr *)&server_addr , sizeof(server_addr)) < 0) {
		log_error("bind failed. Error");
		exit(1);
	}
	listen(sock_server, 3);
	serv->hp = 0;
	serv->sock = sock_server;
	serv->handler = handler;
	pthread_mutex_t * lock = (pthread_mutex_t *)malloc(sizeof(pthread_mutex_t));
	
	if(pthread_mutex_init(lock, NULL) != 0) {
		log_error("Mutex serv->lock failed");
		exit(1);
	}
	serv->lock = lock;

	pthread_create(&pth_server, NULL, server_fn, (void*)serv);
	serv->thread = pth_server;
	log_debug("Started server id-%d", pth_server);
	return pth_server;
}

int ems_send(struct rpi_t *p) {
	int i, j;
	char packet[BB_LEN];
	packet[0] = 0xAA;
	packet[1] = RP_LEN;
	packet[9] = p->group & 0xff;
	packet[10] = p->node & 0xff;
	packet[11] = p->type & 0xff;
	packet[12] = (p->data & 0xffff) >> 8;
	packet[13] = (p->data & 0xff);

	int s_size = serv_list.p;
	log_debug("send_packet: server #: %d", s_size);
	for(i=0; i<s_size; i++) {
		server_t *serv = serv_list.l[i];
		log_debug("For server running socket %d", serv->sock);
		for(j=0; j<serv->hp; j++){
			log_debug("Client[%d] with fd %d", j, serv->clients[j]->sock);
			if(send(serv->clients[j]->sock, packet, BB_LEN, 0) < 0) {
				log_error("send failed");
				return -1;
			}
			log_debug("Unit test: Messsage sent");
		}
	}
	return 1;
}

int ems_destroy(pthread_t s) {

	if(pthread_cancel(s) != 0){
		log_warn("Could not cancel server thread %d", s);
		return -1;
	}

	pthread_join(s, NULL);

	log_info("Stopped server id-%d", s);

	return 0;
}

/*
 * Unit testing functions
 */
int ems_send2(char *ip, int port, int group, int node, int type, int data) {
	struct sockaddr_in server;
	int sock;
	char msg[50];

	if((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
		log_error("Could not create socket");
		return -1;
	}

	server.sin_addr.s_addr = inet_addr(ip);
	server.sin_family = AF_INET;
	server.sin_port = htons(port);

	if(connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
		log_error("Connect failed");
		return -1;
	}

	log_debug("Mock client connected to server");
	msg[0] = 0xBB;
	msg[1] = node & 0xff;
	msg[2] = group & 0xff;
	msg[3] = 3;
	msg[4] = type & 0xff;
	msg[5] = (data & 0xffff) >> 8;
	msg[6] = data & 0xff;

	if(send(sock, msg, 7, 0) < 0) {
		log_error("send failed");
		return -1;
	}
	log_debug("Unit test: Messsage sent");
	
	return sock;
}

struct test_param {
	void (*handler)(char*, int);
	int sock;
};

void *ems_test_client(void *arg) {
	struct test_param *parg = (struct test_param*)arg;
	char magic[2];

	if(recv(parg->sock, magic, 2, MSG_WAITALL) < 0) {
		log_error("Socket closed");
		close(parg->sock);
		return (void*)(intptr_t)-3;
	}

	if((magic[0] & 0xff) == 0xAA) {
		int len = magic[1] & 0xff;			
		char *data = (char*)malloc(sizeof(char) * len);

		if(recv(parg->sock, data, len, MSG_WAITALL) < 0) {
		log_error("Socket closed");
			free(data);
			close(parg->sock);
			return (void*)(intptr_t)-3;
		}

		char *packet = (char*)malloc(sizeof(char) * (len + 2));
		memcpy(packet, magic, 2);
		memcpy(&packet[2], data, len);

		parg->handler(packet, len + 2);
		free(data);
		free(packet);
		close(parg->sock);
		return (void*)(intptr_t)0;
	} else {
		log_error("Wrong magic byte");
		return (void*)(intptr_t)-4;
	}

}

pthread_t ems_test_run_client(char *ip, int port, void (*handler)(char*, int)){

	pthread_t th_client;
	int sock;
	struct sockaddr_in server;

	sock = socket(AF_INET, SOCK_STREAM, 0);
	if(sock == -1) {
		log_error("Could not create socket");
		exit(1);
	}
	log_debug("Socket created");

	server.sin_addr.s_addr = inet_addr(ip);
	server.sin_family = AF_INET;
	server.sin_port = htons(port);

	if(connect(sock, (struct sockaddr*)&server, sizeof(server)) < 0) {
		log_error("Connect failed");
		exit(1);
	}
	log_debug("Connected socket fd: %d", sock);

	struct test_param *param =  (struct test_param *)malloc(sizeof(struct test_param));
	param->handler = handler;
	param->sock = sock;

	pthread_create(&th_client, NULL, ems_test_client, (void *)param);
	return th_client;
}
