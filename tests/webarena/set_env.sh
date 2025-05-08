# BASE_URL=<YOUR_SERVER_URL_HERE>  # example: "http://myazuremachine.eastus.cloudapp.azure.com"
# Automatically retrieve the IP address of the machine
BASE_URL="http://$(hostname -I | awk '{print $1}')"

# webarena environment variables (change ports as needed)
export WA_SHOPPING="$BASE_URL:8082/"
export WA_SHOPPING_ADMIN="$BASE_URL:9083/admin"
export WA_REDDIT="$BASE_URL:8080"
export WA_GITLAB="$BASE_URL:9001"
export WA_WIKIPEDIA="$BASE_URL:8081/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
export WA_MAP="$BASE_URL:443"
export WA_HOMEPAGE="$BASE_URL:80"

# if your webarena instance offers the FULL_RESET feature (optional)
# export WA_FULL_RESET="$BASE_URL:7565"

# otherwise, be sure to NOT set WA_FULL_RESET, or set it to an empty string
export WA_FULL_RESET=""