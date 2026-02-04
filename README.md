# air-app-vers

- Ref. https://github.com/untillpro/airs-design/blob/main/uspecs/specs/devops/release/app-vers--td.md

## Run tests

```bash
# Install dependencies
pip install coverage pyyaml

# Run tests
python -m unittest discover scripts -v

# Or, run tests with coverage and generate a report
coverage run -m unittest discover scripts
coverage html
```

## Manual validate

```bash
./validate.sh
```
