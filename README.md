# AI-developer

## -- protect the env variables

encrypt
```sh
sops encrypt --age PUBLIC_KEY .env > enc.env
```

decrypt
```sh
SOPS_AGE_KEY_FILE=../key.txt sops decrypt enc.env > .env
```