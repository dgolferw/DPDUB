from utils.market import get_bars
bars = get_bars(['NVDA'], days=7)
df = bars.get('NVDA')
print('Columns:', df.columns.tolist())
print('Index names:', df.index.names)
print(df.head(2))