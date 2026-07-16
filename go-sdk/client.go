package aquastat

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
)

type Client struct {
	APIURL     string
	APIKey     string
	HTTPClient *http.Client
}

type EstimateResponse struct {
	Datacenter struct {
		ID         string `json:"id"`
		Provider   string `json:"provider"`
		RegionSlug string `json:"region_slug"`
	} `json:"datacenter"`
}

type RouteWorkloadRequest struct {
	JobDurationHours float64  `json:"job_duration_hours"`
	ComputeDemandMwh float64  `json:"compute_demand_mwh"`
	CandidateRegions []string `json:"candidate_regions"`
}

func NewClient(apiURL, apiKey string, httpClient *http.Client) *Client {
	if httpClient == nil {
		httpClient = http.DefaultClient
	}
	return &Client{APIURL: apiURL, APIKey: apiKey, HTTPClient: httpClient}
}

func (c *Client) Estimate(ctx context.Context, provider, region string, loadMW float64) (*EstimateResponse, error) {
	u, _ := url.Parse(fmt.Sprintf("%s/estimate", c.APIURL))
	q := u.Query()
	q.Set("provider", provider)
	q.Set("region", region)
	q.Set("load_mw", fmt.Sprintf("%f", loadMW))
	u.RawQuery = q.Encode()
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, u.String(), nil)
	if c.APIKey != "" {
		req.Header.Set("X-API-Key", c.APIKey)
	}
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var parsed EstimateResponse
	if err := json.NewDecoder(resp.Body).Decode(&parsed); err != nil {
		return nil, err
	}
	return &parsed, nil
}

func (c *Client) RouteWorkload(ctx context.Context, payload RouteWorkloadRequest) (*map[string]any, error) {
	body, _ := json.Marshal(payload)
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, fmt.Sprintf("%s/route-workload", c.APIURL), bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("X-API-Key", c.APIKey)
	}
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var parsed map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&parsed); err != nil {
		return nil, err
	}
	return &parsed, nil
}
