package config

import (
	"github.com/kelseyhightower/envconfig"
)

type config struct {
	AdminUsername string `envconfig:"admin_username" default:"admin"`
	AdminPassword string `envconfig:"admin_password" required:"true"`
	Port          int    `envconfig:"port" default:"9000"`
	DBFile        string `envconfig:"db_file" default:"data.boltdb"`
}

func Parse() (*config, error) {
	c := &config{}
	err := envconfig.Process("", c)
	if err != nil {
		return nil, err
	}
	return c, nil
}
