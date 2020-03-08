import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score

def lin_regplot(X, y, model):
    plt.scatter(X, y, c='steelblue', edgecolor='white', s=70)
    plt.plot(X, model.predict(X), color='black', lw=2)
    return None

df = pd.read_json('environment_log_data.json')

regression_pairs = {'Temp and Hum Performance': [['Output Temp', 'Real Temperature', 0], ['Output Humidity', 'Real Humidity', 0], ['Raw Temperature', 'Real Temperature', 0], ['Raw Humidity', 'Real Humidity', 0]],
                    'Gas Sensor Performance': [['Real Temperature', 'RedRS', 23], ['Raw Temperature', 'RedRS', 23], ['Real Humidity', 'RedRS', 50], ['Raw Humidity', 'RedRS', 50], ['Bar', 'RedRS', 1013],
                                               ['Real Temperature', 'OxiRS', 23], ['Raw Temperature', 'OxiRS', 23], ['Real Humidity', 'OxiRS', 50], ['Raw Humidity', 'OxiRS', 50], ['Bar', 'OxiRS', 1013],
                                               ['Real Temperature', 'NH3RS', 23], ['Raw Temperature', 'NH3RS', 23], ['Real Humidity', 'NH3RS', 50], ['Raw Humidity', 'NH3RS', 50], ['Bar', 'NH3RS', 1013]]}
regression_summary = {performance_type:{} for performance_type in regression_pairs}
print(regression_summary)

for performance_type in regression_pairs:
    for pair in range(len(regression_pairs[performance_type])):
        X = df[[regression_pairs[performance_type][pair][0]]].values - regression_pairs[performance_type][pair][2]
        y = df[[regression_pairs[performance_type][pair][1]]].values
        regr = LinearRegression()
        quadratic = PolynomialFeatures(degree=2)
        cubic = PolynomialFeatures(degree=3)
        X_quad = quadratic.fit_transform(X)
        X_cubic = cubic.fit_transform(X)
        X_fit = np.arange(X.min(), X.max(), 1) [:, np.newaxis]
        regr = regr.fit(X, y)
        y_lin_fit = regr.predict(X_fit)
        linear_r2 = r2_score(y, regr.predict(X))
        print('')
        print(regression_pairs[performance_type][pair][0] + ' and ' + regression_pairs[performance_type][pair][1])
        print('Slope: %.4f' % regr.coef_[0])
        print('Intercept: %.4f' % regr.intercept_)
        print('R2: %.2f' % linear_r2)
        regression_summary[performance_type][regression_pairs[performance_type][pair][0] + ' ' + regression_pairs[performance_type][pair][1]] = {'Slope': regr.coef_[0], 'Intercept': regr.intercept_, 'R2': linear_r2}
        regr = regr.fit(X_quad, y)
        y_quad_fit = regr.predict(quadratic.fit_transform(X_fit))
        reg_label = "Inliers coef:%s - b:%0.4f" % \
                    (np.array2string(regr.coef_,
                                     formatter={'float_kind': lambda fk: "%.4f" % fk}),
                    regr.intercept_)
        print('Quad Fit', reg_label)
        quadratic_r2 = r2_score(y, regr.predict(X_quad))
        print('R2: %.2f' % quadratic_r2)
        regr = regr.fit(X_cubic, y)
        y_cubic_fit = regr.predict(cubic.fit_transform(X_fit))
        reg_label = "Inliers coef:%s - b:%0.5f" % \
                    (np.array2string(regr.coef_,
                                     formatter={'float_kind': lambda fk: "%.5f" % fk}),
                    regr.intercept_)
        print('Cubic Fit', reg_label)
        cubic_r2 = r2_score(y, regr.predict(X_cubic))
        print('R2: %.2f' % cubic_r2)
        plt.scatter(X, y, label='training points', color='lightgray')
        plt.plot(X_fit, y_lin_fit, label='linear (d=1), $R^2=%.2f$' % linear_r2, color='blue', lw=2, linestyle=':')
        plt.plot(X_fit, y_quad_fit, label='quadratic (d=2), $R^2=%.2f$' % quadratic_r2, color='red', lw=2, linestyle='-')
        plt.plot(X_fit, y_cubic_fit, label='cubic (d=3), $R^2=%.2f$' % cubic_r2, color='green', lw=2, linestyle='--') 
        plt.xlabel(regression_pairs[performance_type][pair][0])
        plt.ylabel(regression_pairs[performance_type][pair][1])
        plt.legend(loc='lower right')
        plt.show()

for pt in regression_summary:
    print('')
    print(pt, 'Summary')
    for pair in (regression_summary[pt]):
        print(pair, regression_summary[pt][pair])



# Improved Temp and Hum Performance

X = df[['Raw Temperature']].values
y = df[['CPU Temperature']].values - df[['Raw Temperature']].values
improved_cpu_temp_factor = y


regr = LinearRegression()
quadratic = PolynomialFeatures(degree=2)
cubic = PolynomialFeatures(degree=3)
X_quad = quadratic.fit_transform(X)
X_cubic = cubic.fit_transform(X)

X_fit = np.arange(X.min(), X.max(), 1) [:, np.newaxis]
regr = regr.fit(X, y)
y_lin_fit = regr.predict(X_fit)
linear_r2 = r2_score(y, regr.predict(X))
print('')
print('Improved CPU Temp Factor')
print('Slope: %.4f' % regr.coef_[0])
print('Intercept: %.4f' % regr.intercept_)
print('R2: %.2f' % linear_r2)
improved_cpu_temp_factor_slope =  regr.coef_[0]
improved_cpu_temp_factor_intercept = regr.intercept_
improved_cpu_temp_factor_r2 = linear_r2

regr = regr.fit(X_quad, y)
y_quad_fit = regr.predict(quadratic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.4f" % \
            (np.array2string(regr.coef_,
                             formatter={'float_kind': lambda fk: "%.4f" % fk}),
            regr.intercept_)
print('Quad Fit', reg_label)
quadratic_r2 = r2_score(y, regr.predict(X_quad))
print('R2: %.2f' % quadratic_r2)
regr = regr.fit(X_cubic, y)
y_cubic_fit = regr.predict(cubic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.5f" % \
                    (np.array2string(regr.coef_,
                                     formatter={'float_kind': lambda fk: "%.5f" % fk}),
                    regr.intercept_)
print('Cubic Fit', reg_label)
cubic_r2 = r2_score(y, regr.predict(X_cubic))
print('R2: %.2f' % cubic_r2)

plt.scatter(X, y, label='training points', color='lightgray')

plt.plot(X_fit, y_lin_fit, label='linear (d=1), $R^2=%.2f$' % linear_r2, color='blue', lw=2, linestyle=':')

plt.plot(X_fit, y_quad_fit, label='quadratic (d=2), $R^2=%.2f$' % quadratic_r2, color='red', lw=2, linestyle='-')

plt.plot(X_fit, y_cubic_fit, label='cubic (d=3), $R^2=%.2f$' % cubic_r2, color='green', lw=2, linestyle='--')

plt.xlabel('Raw Temperature')
plt.ylabel('Current CPU Temp - Raw Temp')
plt.legend(loc='lower right')
plt.show()

improved_raw_temp_without_cpu_impact = df[['Raw Temperature']].values - (improved_cpu_temp_factor_slope * improved_cpu_temp_factor + improved_cpu_temp_factor_intercept)
X = improved_raw_temp_without_cpu_impact
y = df[['Real Temperature']].values

regr = LinearRegression()
quadratic = PolynomialFeatures(degree=2)
cubic = PolynomialFeatures(degree=3)
X_quad = quadratic.fit_transform(X)
X_cubic = cubic.fit_transform(X)

X_fit = np.arange(X.min(), X.max(), 1) [:, np.newaxis]
regr = regr.fit(X, y)
y_lin_fit = regr.predict(X_fit)
linear_r2 = r2_score(y, regr.predict(X))
print('')
print('Improved Comp Temp')
print('Slope: %.4f' % regr.coef_[0])
print('Intercept: %.4f' % regr.intercept_)
improved_comp_temp_slope = regr.coef_[0]
improved_comp_temp_intercept = regr.intercept_
improved_comp_temp_r2 = linear_r2
regr = regr.fit(X_quad, y)
y_quad_fit = regr.predict(quadratic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.4f" % \
            (np.array2string(regr.coef_,
                             formatter={'float_kind': lambda fk: "%.4f" % fk}),
            regr.intercept_)
print('R2: %.2f' % linear_r2)
print('Quad Fit', reg_label)
quadratic_r2 = r2_score(y, regr.predict(X_quad))
print('R2: %.2f' % quadratic_r2)
regr = regr.fit(X_cubic, y)
y_cubic_fit = regr.predict(cubic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.5f" % \
                    (np.array2string(regr.coef_,
                                     formatter={'float_kind': lambda fk: "%.5f" % fk}),
                    regr.intercept_)
print('Cubic Fit', reg_label)
print('R2: %.2f' % cubic_r2)
cubic_r2 = r2_score(y, regr.predict(X_cubic))

plt.scatter(X, y, label='training points', color='lightgray')

plt.plot(X_fit, y_lin_fit, label='linear (d=1), $R^2=%.2f$' % linear_r2, color='blue', lw=2, linestyle=':')

plt.plot(X_fit, y_quad_fit, label='quadratic (d=2), $R^2=%.2f$' % quadratic_r2, color='red', lw=2, linestyle='-')

plt.plot(X_fit, y_cubic_fit, label='cubic (d=3), $R^2=%.2f$' % cubic_r2, color='green', lw=2, linestyle='--')
      
plt.xlabel('Improved Raw Temp w/o CPU Impact')
plt.ylabel('Real Temperature')
plt.legend(loc='lower right')
plt.show()

# Show Improved Temp Performance
X = improved_raw_temp_without_cpu_impact * improved_comp_temp_slope + improved_comp_temp_intercept
improved_output_temp = X
y = df[['Real Temperature']].values

regr = LinearRegression()
quadratic = PolynomialFeatures(degree=2)
cubic = PolynomialFeatures(degree=3)
X_quad = quadratic.fit_transform(X)
X_cubic = cubic.fit_transform(X)

X_fit = np.arange(X.min(), X.max(), 1) [:, np.newaxis]
regr = regr.fit(X, y)
y_lin_fit = regr.predict(X_fit)
linear_r2 = r2_score(y, regr.predict(X))
print('')
print('Improved Temp Performance')
print('Slope: %.4f' % regr.coef_[0])
print('Intercept: %.4f' % regr.intercept_)
print('R2: %.2f' % linear_r2)
improved_temp_slope =  regr.coef_[0]
improved_temp_intercept = regr.intercept_
improved_temp_r2 = linear_r2
regr = regr.fit(X_quad, y)
y_quad_fit = regr.predict(quadratic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.4f" % \
            (np.array2string(regr.coef_,
                             formatter={'float_kind': lambda fk: "%.4f" % fk}),
            regr.intercept_)
print('Quad Fit', reg_label)
quadratic_r2 = r2_score(y, regr.predict(X_quad))
print('R2: %.2f' % quadratic_r2)
regr = regr.fit(X_cubic, y)
y_cubic_fit = regr.predict(cubic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.5f" % \
                    (np.array2string(regr.coef_,
                                     formatter={'float_kind': lambda fk: "%.5f" % fk}),
                    regr.intercept_)
print('Cubic Fit', reg_label)
cubic_r2 = r2_score(y, regr.predict(X_cubic))
print('R2: %.2f' % cubic_r2)

plt.scatter(X, y, label='training points', color='lightgray')

plt.plot(X_fit, y_lin_fit, label='linear (d=1), $R^2=%.2f$' % linear_r2, color='blue', lw=2, linestyle=':')

plt.plot(X_fit, y_quad_fit, label='quadratic (d=2), $R^2=%.2f$' % quadratic_r2, color='red', lw=2, linestyle='-')

plt.plot(X_fit, y_cubic_fit, label='cubic (d=3), $R^2=%.2f$' % cubic_r2, color='green', lw=2, linestyle='--')

plt.xlabel('Improved Output Temp')
plt.ylabel('Real Temperature')
plt.legend(loc='lower right')
plt.show()


X =100*(np.exp((17.625*df[['Dew Point']].values)/(243.04+df[['Dew Point']].values))/np.exp((17.625*improved_output_temp)/(243.04+improved_output_temp)))
y = df[['Real Humidity']].values

regr = LinearRegression()
quadratic = PolynomialFeatures(degree=2)
cubic = PolynomialFeatures(degree=3)
X_quad = quadratic.fit_transform(X)
X_cubic = cubic.fit_transform(X)

X_fit = np.arange(X.min(), X.max(), 1) [:, np.newaxis]
regr = regr.fit(X, y)
y_lin_fit = regr.predict(X_fit)
linear_r2 = r2_score(y, regr.predict(X))
print('')
print('Improved Output Humidity')
print('Slope: %.4f' % regr.coef_[0])
print('Intercept: %.4f' % regr.intercept_)
print('R2: %.2f' % linear_r2)
improved_comp_hum_slope = regr.coef_[0]
improved_comp_hum_intercept = regr.intercept_
improved_comp_hum_r2 = linear_r2

regr = regr.fit(X_quad, y)
y_quad_fit = regr.predict(quadratic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.4f" % \
            (np.array2string(regr.coef_,
                             formatter={'float_kind': lambda fk: "%.4f" % fk}),
            regr.intercept_)
print('Quad Fit', reg_label)
quadratic_r2 = r2_score(y, regr.predict(X_quad))
print('R2: %.2f' % quadratic_r2)
regr = regr.fit(X_cubic, y)
y_cubic_fit = regr.predict(cubic.fit_transform(X_fit))
reg_label = "Inliers coef:%s - b:%0.5f" % \
                    (np.array2string(regr.coef_,
                                     formatter={'float_kind': lambda fk: "%.5f" % fk}),
                    regr.intercept_)
print('Cubic Fit', reg_label)
cubic_r2 = r2_score(y, regr.predict(X_cubic))
print('R2: %.2f' % cubic_r2)

plt.scatter(X, y, label='training points', color='lightgray')

plt.plot(X_fit, y_lin_fit, label='linear (d=1), $R^2=%.2f$' % linear_r2, color='blue', lw=2, linestyle=':')

plt.plot(X_fit, y_quad_fit, label='quadratic (d=2), $R^2=%.2f$' % quadratic_r2, color='red', lw=2, linestyle='-')

plt.plot(X_fit, y_cubic_fit, label='cubic (d=3), $R^2=%.2f$' % cubic_r2, color='green', lw=2, linestyle='--')

plt.xlabel('Improved Humidity')
plt.ylabel('Real Humidity')
plt.legend(loc='lower right')
plt.show()


print('')
print('IMPROVED TEMP AND HUM COMPENSATION SUMMARY')
print('CPU Temp Factor. Slope:', improved_cpu_temp_factor_slope, 'Intercept:', improved_cpu_temp_factor_intercept, 'R2:', improved_cpu_temp_factor_r2)
print('Improved Comp Temp. Slope:', improved_comp_temp_slope, 'Intercept:', improved_comp_temp_intercept, 'R2:', improved_comp_temp_r2)
print('Improved Temp. Slope:', improved_temp_slope, 'Intercept:', improved_temp_intercept, 'R2:', improved_temp_r2)
print('Improved Comp Hum. Slope:', improved_comp_hum_slope, 'Intercept:', improved_comp_hum_intercept, 'R2:', improved_comp_hum_r2)
print('')

# Acknowledgement: Thanks to https://www.packtpub.com/au/data/python-machine-learning-third-edition




