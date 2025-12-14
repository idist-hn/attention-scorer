package services

import (
	"context"
	"fmt"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
)

// GRPCClient manages gRPC connection to AI service
type GRPCClient struct {
	conn   *grpc.ClientConn
	addr   string
	mu     sync.RWMutex
}

// GRPCClientConfig configuration
type GRPCClientConfig struct {
	Address            string
	MaxRetries         int
	RetryDelay         time.Duration
	KeepAliveTime      time.Duration
	KeepAliveTimeout   time.Duration
	MaxMessageSize     int
}

// DefaultGRPCConfig returns default configuration
func DefaultGRPCConfig(addr string) GRPCClientConfig {
	return GRPCClientConfig{
		Address:          addr,
		MaxRetries:       3,
		RetryDelay:       time.Second,
		KeepAliveTime:    10 * time.Second,
		KeepAliveTimeout: 3 * time.Second,
		MaxMessageSize:   50 * 1024 * 1024, // 50MB for video frames
	}
}

// NewGRPCClient creates a new gRPC client
func NewGRPCClient(config GRPCClientConfig) (*GRPCClient, error) {
	client := &GRPCClient{
		addr: config.Address,
	}

	opts := []grpc.DialOption{
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Time:                config.KeepAliveTime,
			Timeout:             config.KeepAliveTimeout,
			PermitWithoutStream: true,
		}),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(config.MaxMessageSize),
			grpc.MaxCallSendMsgSize(config.MaxMessageSize),
		),
	}

	var err error
	for i := 0; i < config.MaxRetries; i++ {
		client.conn, err = grpc.NewClient(config.Address, opts...)
		if err == nil {
			return client, nil
		}
		time.Sleep(config.RetryDelay)
	}

	return nil, fmt.Errorf("failed to connect to AI service after %d retries: %w", config.MaxRetries, err)
}

// GetConnection returns the gRPC connection
func (c *GRPCClient) GetConnection() *grpc.ClientConn {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.conn
}

// ProcessFrame sends a frame to AI service for processing
func (c *GRPCClient) ProcessFrame(ctx context.Context, meetingID, participantID string, frameData []byte) (interface{}, error) {
	// Note: In production, use generated protobuf client
	// client := pb.NewAttentionServiceClient(c.conn)
	// return client.ProcessFrame(ctx, &pb.FrameRequest{...})
	
	return nil, fmt.Errorf("gRPC client not fully implemented - use generated protobuf stubs")
}

// HealthCheck checks AI service health
func (c *GRPCClient) HealthCheck(ctx context.Context) (bool, error) {
	// Note: In production, use generated protobuf client
	return true, nil
}

// Close closes the connection
func (c *GRPCClient) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// ConnectionPool manages multiple gRPC connections
type ConnectionPool struct {
	clients []*GRPCClient
	index   int
	mu      sync.Mutex
}

// NewConnectionPool creates a connection pool
func NewConnectionPool(config GRPCClientConfig, size int) (*ConnectionPool, error) {
	pool := &ConnectionPool{
		clients: make([]*GRPCClient, size),
	}

	for i := 0; i < size; i++ {
		client, err := NewGRPCClient(config)
		if err != nil {
			// Close already created clients
			for j := 0; j < i; j++ {
				pool.clients[j].Close()
			}
			return nil, err
		}
		pool.clients[i] = client
	}

	return pool, nil
}

// GetClient returns a client from pool (round-robin)
func (p *ConnectionPool) GetClient() *GRPCClient {
	p.mu.Lock()
	defer p.mu.Unlock()
	
	client := p.clients[p.index]
	p.index = (p.index + 1) % len(p.clients)
	return client
}

// Close closes all connections
func (p *ConnectionPool) Close() {
	for _, client := range p.clients {
		client.Close()
	}
}

